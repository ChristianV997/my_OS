import { useCallback, useEffect, useRef, useState } from "react";
import type { RuntimeSnapshot, TaskInventory, WsEvent } from "../types";
import { useWebSocket } from "./useWebSocket";

const CAPITAL_HISTORY_MAX = 200;

export function useMetrics() {
  const [snapshot, setSnapshot] = useState<RuntimeSnapshot | null>(null);
  const [capitalHistory, setCapitalHistory] = useState<{ t: number; v: number }[]>([]);
  const [roasHistory, setRoasHistory] = useState<{ t: number; v: number }[]>([]);
  const [lastWorker, setLastWorker] = useState<{ name: string; ts: number } | null>(null);
  const [taskInventory, setTaskInventory] = useState<TaskInventory | null>(null);

  // Fetch initial snapshot via REST before WS connects
  useEffect(() => {
    fetch("/api/snapshot")
      .then((r) => r.json())
      .then((data) => {
        if (data && data.cycle !== undefined) setSnapshot(data as RuntimeSnapshot);
      })
      .catch(() => {/* backend may not be ready yet */});
  }, []);

  const handleEvent = useCallback((ev: WsEvent) => {
    if (ev.type === "snapshot") {
      const snap = ev as RuntimeSnapshot;
      setSnapshot(snap);
      setCapitalHistory((h) => {
        const next = [...h, { t: snap.ts, v: snap.capital }];
        return next.length > CAPITAL_HISTORY_MAX ? next.slice(-CAPITAL_HISTORY_MAX) : next;
      });
      setRoasHistory((h) => {
        const next = [...h, { t: snap.ts, v: snap.avg_roas }];
        return next.length > CAPITAL_HISTORY_MAX ? next.slice(-CAPITAL_HISTORY_MAX) : next;
      });
    } else if (ev.type === "worker") {
      const w = ev as { type: "worker"; worker: string; ts: number };
      setLastWorker({ name: w.worker, ts: w.ts });
    } else if (ev.type === "tick") {
      const t = ev as { type: "tick"; phase: string; avg_roas: number; capital: number; ts: number };
      setSnapshot((s) => s ? { ...s, phase: t.phase as RuntimeSnapshot["phase"], avg_roas: t.avg_roas, capital: t.capital } : s);
    } else if (ev.type === "task_inventory") {
      setTaskInventory(ev as TaskInventory);
    }
  }, []);

  const { connected } = useWebSocket(handleEvent);

  return { snapshot, capitalHistory, roasHistory, lastWorker, taskInventory, connected };
}
