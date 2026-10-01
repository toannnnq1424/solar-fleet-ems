# Bluesun: model-aware integration

Researched 19 September 2026. No direct public Bluesun cloud API contract was verified. This does not prove that no private/partner API exists. The product must distinguish manufacturer, actual model/OEM, logger and cloud platform.

| Device evidence | Candidate path | Confidence and applicability |
|---|---|---|
| BSE15KH3 | ha-solarman `afore_hybrid` profile; compatible SOLARMAN logger if present | [Maintainer's supported-device table](https://github.com/davidrapan/ha-solarman/wiki/Supported-Devices) lists this exact model. Community evidence, not our hardware acceptance; logger/firmware must be confirmed |
| BSE12KH3 | ha-solarman `megarevo_r-3h` profile; compatible SOLARMAN logger if present | Same maintainer table; must not reuse the BSE15KH3 map |
| BSE6KL1 | Determine its actual logger/platform first | [Official two-page datasheet](https://www.bluesunpv.com/wp-content/uploads/2024/11/ESS_BSE6KL1_EN_v2406_Rev-01.pdf) mentions a cloud platform and communication interfaces; it does not establish a SOLARMAN API/register contract |
| BSM-5500BLV-48DA | Investigate SmartESS / Eybond | [Official manual](https://www.bluesunpv.com/wp-content/uploads/2024/11/BSM-5500BLV-48DA-User-Manual-V2.0.pdf). This path is not interchangeable with SOLARMAN |

## Open-source adoption

[pysolarmanv5](https://github.com/jmccrohan/pysolarmanv5) is an optional dependency pinned at **3.0.6**, MIT, authored by Jonathan McCrohan. Source examined at commit `8cfe84650f48f0803c32b3c4ca061364abd9cf49`: constructor with address/logger serial/port/unit ID, `read_holding_registers`, `read_input_registers`, and `disconnect`. We expose only these read methods in `local_solarman.py`. Upstream also has write/discovery tools; SolarOne does not invoke or expose them through its UI/API.

The library implements Modbus RTU carried in SOLARMAN V5 frames, commonly port 8899. It is not generic Modbus TCP and is not compatible with every logger (upstream explicitly excludes Solis S3-WIFI-ST). The deployment must identify the protocol before selecting this driver.

[ha-solarman](https://github.com/davidrapan/ha-solarman), MIT, David Rapan and contributors, was reviewed at commit `ac1d88b83268beeb0511b8a1b7fc8e17deddc044`. Its wiki is separate and mutable; retrieval date is recorded above. Its device profiles are **research inputs**, not executable configuration imported into SolarOne. No HA YAML, templates, services, or write mappings are executed. We have not copied the entire integration or declared its whole device list supported.

The Bluesun spreadsheet attachment linked from the wiki was not successfully retrieved; its contents have not been used as register evidence.

## Cloud route

Select **Bluesun → SOLARMAN account** only when that plant is actually present in an authorized SOLARMAN account. The stored transport remains `SOLARMAN`; `equipment_brand=Bluesun` is the user's declared brand, not an automatically verified OEM identity.

As of 24 September, **Bluesun → SmartESS / Eybond** also opens a real read connector form with explicit DessMonitor or ShineMonitor platform selection. It signs requests, discovers plant/collector/device routes and retains native telemetry without inferred units or source timestamps. The shared controller, device views and collection policies consume those observations. This is not complete support for every Bluesun model: see [Eybond implementation and gaps](eybond-read-integration.md). BMS Cloud and other unverified platforms have no generic fallback.

## Local route

On the site agent, install `pip install 'solar-fleet-ems[local-solarman]'`. Enroll an agent and explicitly register its allowed device in the shared UI. Prepare a JSON `CollectionProfile` containing agent/device IDs, private IPv4, logger serial/model/firmware, inverter model/firmware, unit ID, an evidence reference, reviewer, and explicit read blocks (`function`: 3 or 4, `address`, `count`). The exact schema is `local_solarman.CollectionProfile`; no addresses are assumed from the brand.

Run `solar-fleet-agent --spool <local-spool.db> collect-solarman --profile <reviewed-profile.json>` to read one bounded collection and enqueue it. Then `solar-fleet-agent --spool <local-spool.db> flush --controller <controller-base-url>` using `SOLAR_AGENT_TOKEN` from the local environment. HTTPS or a loopback tunnel is required for remote transport. A failed flush keeps the batch for retry; a collection failure queues no partial batch.

Values remain raw uint16 native registers with no invented scale, unit, sign or physical canonical metric. Timestamps indicate local acquisition, not the inverter's internal sample clock. Server ingress marks these points UNVERIFIED. Limits: one specified private host, at most 64 blocks/1000 registers, 125 registers per request, 5-second socket timeout, no bus/network scan. Review labels record operator input; they are not cryptographic proof of approval.

Still required: exact register semantics, commissioning/acceptance, deployable site-agent service, tested cloud/local coexistence, and per-model canonical/control profiles. Register reading alone does not complete Bluesun production support.


## Đối chiếu bổ sung 20/09/2026

Trang chính thức [BSE15/20/30KH3](https://www.bluesunpv.com/20kw-30kw-three-phase-ess-hybrid-solar-inverter/) nêu TOU, anti-feed-in, monitoring và firmware từ xa. Đây là chức năng sản phẩm; chưa phải API, địa chỉ cloud hoặc quyền tài khoản. Không suy ra cùng protocol cho ba model.

[Catalog pin chính thức](https://www.bluesunpv.com/wp-content/uploads/2024/09/BLUESUNESS-BATTERY-CATALOG.pdf) mô tả BMS lên cloud trong chỉ mục tìm kiếm. Chưa trích xuất/đối chiếu đầy đủ PDF 14 MB trong đợt này; endpoint, auth, OTA và applicability chưa xác minh. BMS Cloud tách khỏi inverter và chưa có transport.

## Kiến trúc 3 nhánh đã hiện thực hóa trong Core — 01/10/2026

Đã triển khai module `src/solar_fleet/adapters/bluesun_adapter.py` với bộ phân giải `BluesunMultiPlatformResolver`, phân định rạch ròi 3 nhánh vận hành độc lập:
1. **Bluesun BSM (e.g. BSM-5500BLV-48DA)**: Kết nối qua nền tảng SmartESS / Eybond Wi-Fi Plug Pro, giao tiếp Modbus RTU / Eybond protocol (port 8000 Modbus TCP hoặc reverse UDP). Hỗ trợ chế độ SolarFirst, UtilityFirst, SBU.
2. **Bluesun BSE Hybrid (e.g. BSE6KL1, BSE20/30KH3)**: Kết nối qua Bluesun Hybrid Cloud Platform, hỗ trợ chống phát ngược Zero-Export (Anti-feed-in), TOU peak-shaving và điều khiển máy phát.
3. **Bluesun ESS Battery**: Kênh giám sát BMS Cloud chuyên dụng cho pack pin Lithium LFP 51.2V, đọc điện áp cell, nhiệt độ cell và cảnh báo BMS.
Hệ thống loại bỏ hoàn toàn giả định "Bluesun là một adapter monolithic", đảm bảo tính tương thích và an toàn điện vật lý.

