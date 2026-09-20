// Scoped invalidations over a cookie-authenticated, read-only WebSocket.
// Existing forms are never replaced automatically while someone is editing.
export function createLiveFeed({ changed, status, authenticated }) {
  let socket,
    timer,
    stopped = true,
    delay = 1000,
    cursor = 0;
  function connect() {
    if (stopped || !authenticated()) return;
    const url = new URL("/api/stream", location.href);
    url.protocol = location.protocol === "https:" ? "wss:" : "ws:";
    url.searchParams.set("cursor", cursor);
    socket = new WebSocket(url);
    status("CONNECTING");
    socket.onopen = () => {
      delay = 1000;
      status("CONNECTED");
    };
    socket.onmessage = (event) => {
      let packet;
      try {
        packet = JSON.parse(event.data);
      } catch {
        socket.close();
        return;
      }
      if (Number.isSafeInteger(packet.cursor)) cursor = packet.cursor;
      if (packet.type === "changes" || packet.type === "reset") changed(packet);
    };
    socket.onclose = (event) => {
      socket = null;
      status(event.code === 1008 ? "REAUTHENTICATE" : "DISCONNECTED");
      if (event.code === 1008 || stopped) return;
      timer = setTimeout(connect, delay);
      delay = Math.min(delay * 2, 30000);
    };
    socket.onerror = () => socket?.close();
  }
  return {
    start() {
      if (!stopped) return;
      stopped = false;
      cursor = 0;
      connect();
    },
    stop() {
      stopped = true;
      clearTimeout(timer);
      socket?.close();
      socket = null;
    },
  };
}
