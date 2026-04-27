import { useCallback, useState } from "react";
import type { RuntimeSnapshot, TaskInventory, WsEvent } from "../types";
import { useWebSocket } from "./useWebSocket";
import { useRuntimeStore } from "../runtimeStore";

const CAPITAL_HISTORY_MAX = 200;

const isSnapshot = (t: string) => t === "snapshot" || t === "runtime.snapshot";
const isTick = (t: string) => t === "tick" || t === "orchestrator.tick";
const isWorker = (t: string) => t === "worker" || t === "worker.health";

export function useMetrics() {
  const [snapshot, setSnapshot] = useState<RuntimeSnapshot | null>(null);
  const [capitalHistory, setCapitalHistory] = useState<{ t: number; v: number }[]>([]);
  const [roasHistory, setRoasHistory] = useState<{ t: number; v: number }[]>([]);
  const [lastWorker, setLastWorker] = useState<{ name: string; ts: number } | null>(null);
  const [taskInventory, setTaskInventory] = useState<TaskInventory | null>(null);
  const appendEvent = useRuntimeStore((state) => state.append);

  const handleEvent = useCallback((ev: WsEvent) => {
    appendEvent(ev as any);

    const t = ev.type;
    if (isSnapshot(t)) {
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
    } else if (isTick(t)) {
      const tick = ev as { type: string; phase: string; avg_roas: number; capital: number; win_rate?: number; ts: number };
      setSnapshot((s) => (s ? {
        ...s,
        phase: tick.phase as RuntimeSnapshot["phase"],
        avg_roas: tick.avg_roas,
        capital: tick.capital,
        win_rate: tick.win_rate ?? s.win_rate,
      } : s));
    } else if (isWorker(t)) {
      const w = ev as { type: string; worker: string; ts: number };
      setLastWorker({ name: w.worker, ts: w.ts });
    } else if (t === "task_inventory") {
      setTaskInventory(ev as TaskInventory);
    }
  }, [appendEvent]);

  const { connected } = useWebSocket(handleEvent);

  return { snapshot, capitalHistory, roasHistory, lastWorker, taskInventory, connected };
}
