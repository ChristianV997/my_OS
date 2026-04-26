import { useCallback, useEffect, useRef, useState } from "react";
import type { WsEvent } from "../types";

const WS_URL = `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws`;
const RECONNECT_MS = [1000, 2000, 4000, 8000, 16000];

export function useWebSocket(onMessage: (e: WsEvent) => void) {
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const attemptsRef = useRef(0);
  const onMessageRef = useRef(onMessage);
  onMessageRef.current = onMessage;

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      attemptsRef.current = 0;
    };

    ws.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data) as WsEvent;
        onMessageRef.current(data);
      } catch {
        /* ignore malformed frames */
      }
    };

    ws.onclose = () => {
      setConnected(false);
      const delay = RECONNECT_MS[Math.min(attemptsRef.current, RECONNECT_MS.length - 1)];
      attemptsRef.current += 1;
      setTimeout(connect, delay);
    };

    ws.onerror = () => ws.close();
  }, []);

  useEffect(() => {
    connect();
    return () => wsRef.current?.close();
  }, [connect]);

  return { connected };
}
