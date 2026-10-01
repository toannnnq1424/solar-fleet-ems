"""Local agent daemon — polls local inverters and feeds into the shared outbox.

Each configured local device runs in its own polling loop at the configured
cadence. Reads are serialized per device (one in-flight poll at a time).
Failed polls are logged and quarantined; partial/malformed frames fail before
any points enter the durable outbox (maintained from local_models.py principle).

Transport support:
- modbus_tcp:    Growatt SPH/MIN, Sungrow SHx, Huawei SUN2000, Eybond/SMG
- solarman_v5:   SOLARMAN V5 logger encapsulation (any inverter behind a logger)
- goodwe_udp:    GoodWe ES/ET/EH/DT via UDP port 8899
- eybond_local:  Eybond/Bluesun/SMG/PI17 via direct Modbus TCP port 8000

Architecture:
- ``LocalAgentDaemon`` manages N device loops and centralises rate limiting
- ``LocalDevicePoller`` owns one device's connection and sample pipeline
- Samples are written to the provided outbox (async queue)
- Polling does NOT restart on transport errors; it backs off and retries

Usage:
    daemon = LocalAgentDaemon(outbox_queue)
    daemon.add_device(LocalDeviceConfig(
        device_id="inv-001",
        transport="modbus_tcp",
        address="192.168.1.50",
        port=502,
        unit_id=1,
        vendor="growatt",
        model_series="SPH",
        poll_interval_s=30,
    ))
    asyncio.create_task(daemon.run())
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Callable

from .eybond_local import EybondLocalAdapter
from .goodwe_local import GoodWeLocalAdapter
from .interfaces import TelemetrySnapshot
from .modbus_local import ModbusTcpPoller
from .solarman_local import SolarmanV5Poller
from .sunsynk_local import SunsynkLocalAdapter

logger = logging.getLogger(__name__)

# Maximum consecutive failures before a device is quarantined
MAX_CONSECUTIVE_FAILURES = 5
# Back-off between retries after consecutive failures (seconds)
FAILURE_BACKOFF_S = 60.0
# Maximum back-off (capped at this, regardless of failure count)
MAX_BACKOFF_S = 600.0


@dataclass
class LocalDeviceConfig:
    """Configuration for a single locally polled device."""
    device_id: str
    transport: str             # "modbus_tcp" | "solarman_v5" | "goodwe_udp" | "eybond_local"
    address: str               # IPv4 address of inverter / logger
    port: int                  # TCP or UDP port
    vendor: str                # Vendor brand ("growatt" | "sungrow" | "huawei" | "eybond" | "goodwe" | ...)
    model_series: str = ""     # For Modbus profile selection ("SPH" | "SHx" | "SUN2000" | ...)
    unit_id: int = 1           # Modbus unit / slave ID
    logger_serial: int | None = None   # SOLARMAN V5 logger serial number
    poll_interval_s: float = 30.0      # Polling interval in seconds
    timeout_s: float = 5.0             # Per-request timeout
    request_delay_s: float = 0.1      # Delay between register block reads
    extra: dict[str, Any] = field(default_factory=dict)  # Vendor-specific params


@dataclass
class PollResult:
    """Result of one successful poll cycle."""
    device_id: str
    snapshot: TelemetrySnapshot
    polled_at: datetime


@dataclass
class PollFailure:
    """Record of a failed poll attempt."""
    device_id: str
    error: str
    failed_at: datetime
    consecutive_count: int


class LocalDevicePoller:
    """Manages polling for one local device.

    Maintains its own transport instance and back-off state.
    Calls ``on_snapshot`` for each successful poll.
    Calls ``on_failure`` on each failed poll.
    """

    def __init__(
        self,
        config: LocalDeviceConfig,
        on_snapshot: Callable[[PollResult], None],
        on_failure: Callable[[PollFailure], None] | None = None,
    ):
        self.config = config
        self.on_snapshot = on_snapshot
        self.on_failure = on_failure
        self._adapter: Any = None
        self._consecutive_failures = 0
        self._quarantined_until: float = 0.0
        self._lock = asyncio.Lock()
        self._running = False

    def _build_adapter(self) -> Any:
        """Instantiate the correct transport adapter for this device."""
        cfg = self.config
        transport = cfg.transport

        if transport == "goodwe_udp":
            return GoodWeLocalAdapter(
                address=cfg.address,
                port=cfg.port,
                timeout=cfg.timeout_s,
                device_sn=cfg.device_id,
                family=cfg.extra.get("family"),
            )
        if transport == "eybond_local":
            return EybondLocalAdapter(
                address=cfg.address,
                port=cfg.port,
                unit_id=cfg.unit_id,
                timeout=cfg.timeout_s,
                request_delay=cfg.request_delay_s,
            )
        if transport == "modbus_tcp":
            return ModbusTcpPoller(
                device_id=cfg.device_id,
                address=cfg.address,
                port=cfg.port,
                unit_id=cfg.unit_id,
                vendor=cfg.vendor,
                model_series=cfg.model_series,
                timeout=cfg.timeout_s,
                request_delay=cfg.request_delay_s,
            )
        if transport == "solarman_v5":
            if not cfg.logger_serial:
                raise ValueError(f"Device {cfg.device_id}: solarman_v5 requires logger_serial")
            return SolarmanV5Poller(
                device_id=cfg.device_id,
                address=cfg.address,
                port=cfg.port,
                unit_id=cfg.unit_id,
                logger_serial=cfg.logger_serial,
                vendor=cfg.vendor,
                model_series=cfg.model_series,
                timeout=cfg.timeout_s,
                request_delay=cfg.request_delay_s,
            )
        if transport in ("sunsynk_local", "sunsynk_modbus"):
            return SunsynkLocalAdapter(
                address=cfg.address,
                port=cfg.port,
                unit_id=cfg.unit_id,
                timeout=cfg.timeout_s,
                request_delay=cfg.request_delay_s,
                device_sn=cfg.device_id,
            )
        raise ValueError(f"Unknown transport {transport!r} for device {cfg.device_id!r}")

    async def poll_once(self) -> PollResult | None:
        """Perform one telemetry poll. Returns PollResult or None on failure."""
        async with self._lock:
            now = time.monotonic()
            if now < self._quarantined_until:
                remaining = self._quarantined_until - now
                logger.debug(
                    "Device %s quarantined for %.0fs more", self.config.device_id, remaining
                )
                return None

            if self._adapter is None:
                try:
                    self._adapter = self._build_adapter()
                except Exception as exc:
                    logger.error("Device %s: adapter build failed: %s", self.config.device_id, exc)
                    self._handle_failure(str(exc))
                    return None

            try:
                snapshot = await asyncio.wait_for(
                    self._adapter.read_telemetry(),
                    timeout=self.config.timeout_s * 2,
                )
                if not snapshot.online and not snapshot.points:
                    raise RuntimeError("Empty offline snapshot — transport likely unreachable")
                self._consecutive_failures = 0
                result = PollResult(
                    device_id=self.config.device_id,
                    snapshot=snapshot,
                    polled_at=datetime.now(UTC),
                )
                self.on_snapshot(result)
                return result

            except asyncio.TimeoutError:
                self._handle_failure("timeout")
                # Reset adapter after timeout — socket may be wedged
                await self._reset_adapter()
                return None
            except Exception as exc:
                self._handle_failure(str(exc))
                await self._reset_adapter()
                return None

    def _handle_failure(self, error: str) -> None:
        """Record a failure and update back-off state."""
        self._consecutive_failures += 1
        failure = PollFailure(
            device_id=self.config.device_id,
            error=error,
            failed_at=datetime.now(UTC),
            consecutive_count=self._consecutive_failures,
        )
        if self.on_failure:
            self.on_failure(failure)

        if self._consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
            backoff = min(
                FAILURE_BACKOFF_S * (2 ** (self._consecutive_failures - MAX_CONSECUTIVE_FAILURES)),
                MAX_BACKOFF_S,
            )
            self._quarantined_until = time.monotonic() + backoff
            logger.warning(
                "Device %s: %d consecutive failures, quarantined for %.0fs",
                self.config.device_id,
                self._consecutive_failures,
                backoff,
            )
        else:
            logger.warning(
                "Device %s: poll failed (%d/%d): %s",
                self.config.device_id,
                self._consecutive_failures,
                MAX_CONSECUTIVE_FAILURES,
                error,
            )

    async def _reset_adapter(self) -> None:
        """Close and clear the adapter so it will be rebuilt on next poll."""
        if self._adapter is not None:
            try:
                await self._adapter.close()
            except Exception:
                pass
            self._adapter = None

    async def run_loop(self) -> None:
        """Poll in a loop at the configured interval until cancelled."""
        self._running = True
        logger.info(
            "LocalDevicePoller started: %s (%s) @ %s:%d every %.0fs",
            self.config.device_id,
            self.config.transport,
            self.config.address,
            self.config.port,
            self.config.poll_interval_s,
        )
        try:
            while self._running:
                start = time.monotonic()
                await self.poll_once()
                elapsed = time.monotonic() - start
                sleep = max(0, self.config.poll_interval_s - elapsed)
                await asyncio.sleep(sleep)
        except asyncio.CancelledError:
            logger.info("LocalDevicePoller cancelled: %s", self.config.device_id)
        finally:
            await self._reset_adapter()
            self._running = False

    async def stop(self) -> None:
        """Stop the polling loop."""
        self._running = False
        await self._reset_adapter()


class LocalAgentDaemon:
    """Central daemon managing all locally polled devices.

    One polling coroutine per device, coordinated by this daemon.
    Snapshots are delivered to the shared outbox queue.

    Usage:
        outbox = asyncio.Queue()
        daemon = LocalAgentDaemon(outbox)
        daemon.add_device(LocalDeviceConfig(...))
        await daemon.start()  # launches tasks
        # ... later:
        await daemon.stop()
    """

    def __init__(
        self,
        outbox: asyncio.Queue | None = None,
        on_snapshot: Callable[[PollResult], None] | None = None,
        configs: list[LocalDeviceConfig] | None = None,
    ):
        self.outbox = outbox or asyncio.Queue()
        self.on_snapshot = on_snapshot
        self._configs: list[LocalDeviceConfig] = []
        self._pollers: dict[str, LocalDevicePoller] = {}
        self._tasks: dict[str, asyncio.Task] = {}
        self._failure_log: list[PollFailure] = []
        self._running = False
        if configs:
            for c in configs:
                self.add_device(c)

    def poll_all_sync(self) -> list[PollResult]:
        """Synchronously poll all registered devices once and return results."""
        results: list[PollResult] = []

        async def _run():
            for c in self._configs:
                p = self._pollers.get(c.device_id) or LocalDevicePoller(
                    config=c,
                    on_snapshot=self._on_snapshot,
                    on_failure=self._on_failure,
                )
                self._pollers[c.device_id] = p
                res = await p.poll_once()
                results.append(res)

        asyncio.run(_run())
        return results

    def add_device(self, config: LocalDeviceConfig) -> None:
        """Register a device for polling. Dynamically starts task if daemon is running."""
        if config.device_id in self._pollers:
            raise ValueError(f"Device {config.device_id!r} already registered")
        self._configs.append(config)
        if self._running:
            poller = LocalDevicePoller(
                config=config,
                on_snapshot=self._on_snapshot,
                on_failure=self._on_failure,
            )
            self._pollers[config.device_id] = poller
            task = asyncio.create_task(
                poller.run_loop(),
                name=f"local_poll_{config.device_id}",
            )
            self._tasks[config.device_id] = task

    async def remove_device(self, device_id: str) -> None:
        """Unregister a device and stop its polling loop."""
        self._configs = [c for c in self._configs if c.device_id != device_id]
        task = self._tasks.pop(device_id, None)
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        poller = self._pollers.pop(device_id, None)
        if poller:
            await poller.stop()

    def _on_snapshot(self, result: PollResult) -> None:
        """Called by pollers on successful reads. Dispatches to callback and outbox."""
        if self.on_snapshot:
            try:
                self.on_snapshot(result)
            except Exception as exc:
                logger.error("Error in on_snapshot callback for %s: %s", result.device_id, exc)
        if self.outbox:
            try:
                self.outbox.put_nowait(result)
            except asyncio.QueueFull:
                logger.warning(
                    "Outbox full — dropping snapshot for %s", result.device_id
                )

    def _on_failure(self, failure: PollFailure) -> None:
        """Called by pollers on failed reads."""
        self._failure_log.append(failure)
        # Keep only last 1000 failures
        if len(self._failure_log) > 1000:
            self._failure_log = self._failure_log[-500:]

    async def start(self) -> None:
        """Start all device polling loops as background tasks."""
        self._running = True
        for config in self._configs:
            if config.device_id in self._pollers:
                continue
            poller = LocalDevicePoller(
                config=config,
                on_snapshot=self._on_snapshot,
                on_failure=self._on_failure,
            )
            self._pollers[config.device_id] = poller
            task = asyncio.create_task(
                poller.run_loop(),
                name=f"local_poll_{config.device_id}",
            )
            self._tasks[config.device_id] = task
        logger.info(
            "LocalAgentDaemon started with %d devices", len(self._pollers)
        )

    async def stop(self) -> None:
        """Stop all device polling loops."""
        self._running = False
        for task in self._tasks.values():
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks.values(), return_exceptions=True)
        for poller in self._pollers.values():
            await poller.stop()
        self._tasks.clear()
        self._pollers.clear()
        logger.info("LocalAgentDaemon stopped")

    def status(self) -> list[dict]:
        """Return current status of all registered devices."""
        result = []
        for config in self._configs:
            poller = self._pollers.get(config.device_id)
            task = self._tasks.get(config.device_id)
            recent_failures = [
                f for f in self._failure_log if f.device_id == config.device_id
            ][-5:]
            result.append(
                {
                    "device_id": config.device_id,
                    "transport": config.transport,
                    "address": config.address,
                    "port": config.port,
                    "vendor": config.vendor,
                    "running": bool(poller and poller._running),
                    "consecutive_failures": poller._consecutive_failures if poller else 0,
                    "quarantined": (
                        poller._quarantined_until > time.monotonic() if poller else False
                    ),
                    "task_done": task.done() if task else True,
                    "recent_failures": [
                        {"error": f.error, "count": f.consecutive_count}
                        for f in recent_failures
                    ],
                }
            )
        return result
