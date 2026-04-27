import { useCallback, useEffect, useRef, useState } from "react";
import type { RuntimeEnvelope, WsEvent } from "../types";

const WS_URL = `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws/events`;
const RECONNECT_MS = [1000, 2000, 4000, 8000, 16000];

function normalizeEvent(data: RuntimeEnvelope): WsEvent {
  // replay-store hydration frames may arrive wrapped as:
  // { event_id, type, payload: {...} }
  // while legacy runtime frames arrive as raw payloads.
  if (data.payload && typeof data.payload === "object") {
    return {
      ...data.payload,
      event_id: data.event_id,
      replay_hash: data.replay_hash,
      sequence_id: data.sequence_id,
      source: data.source,
      event_version: data.event_version,
      correlation_id: data.correlation_id,
      type: String(data.type),
      ts: Number(data.ts ?? Date.now() / 1000),
    } as WsEvent;
  }

  return data as WsEvent;
}

export function useWebSocket(onMessage: (e: WsEvent) => void) {
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const attemptsRef = useRef(0);
  const onMessageRef = useRef(onMessage);
  onMessageRef.current = onMessage;

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      attemptsRef.current = 0;
    };

    ws.onmessage = (ev) => {
      try {
        const raw = JSON.parse(ev.data) as RuntimeEnvelope;
        const normalized = normalizeEvent(raw);
        onMessageRef.current(normalized);
      } catch {
        // malformed frames are ignored to preserve runtime continuity
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
