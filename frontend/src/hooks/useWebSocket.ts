import { useEffect, useRef } from "react";
import { useWsStore } from "@/store/ws";

const WS_SCHEME = location.protocol === "https:" ? "wss" : "ws";
const WS_URL =
  (import.meta.env.VITE_WS_URL as string | undefined) ??
  `${WS_SCHEME}://${location.host}/ws`;

const BACKOFF = [1000, 2000, 4000, 8000, 16000];

export function useWebSocket() {
  const { setConnected, handleMessage } = useWsStore();
  const ws    = useRef<WebSocket | null>(null);
  const retry = useRef(0);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    function connect() {
      const socket = new WebSocket(WS_URL);
      ws.current   = socket;

      socket.onopen = () => {
        setConnected(true);
        retry.current = 0;
      };

      socket.onmessage = (e) => {
        try { handleMessage(JSON.parse(e.data as string)); } catch { /* skip */ }
      };

      socket.onclose = () => {
        setConnected(false);
        const delay = BACKOFF[Math.min(retry.current, BACKOFF.length - 1)];
        retry.current += 1;
        timer.current = setTimeout(connect, delay);
      };

      socket.onerror = () => socket.close();
    }

    connect();
    return () => {
      if (timer.current) clearTimeout(timer.current);
      ws.current?.close();
    };
  }, [setConnected, handleMessage]);
}
