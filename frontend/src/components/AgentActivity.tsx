import { useMemo } from "react";

import { useRuntimeStore } from "../runtimeStore";
import type { RuntimeEnvelope } from "../types";

interface WorkerRow {
  worker: string;
  status: string;
  sequence: number;
  replayHash: string;
}

function extractWorker(event: RuntimeEnvelope): WorkerRow | null {
  const payload = (event.payload || {}) as Record<string, unknown>;

  const worker = String(
    payload.worker
    || payload.agent
    || payload.module
    || ""
  );

  if (!worker) return null;

  return {
    worker,
    status: String(payload.status || event.type || "active"),
    sequence: Number(event.sequence_id || 0),
    replayHash: String(event.replay_hash || ""),
  };
}

export function AgentActivity() {
  const events = useRuntimeStore((state) => state.events);

  const workers = useMemo(() => {
    const map = new Map<string, WorkerRow>();

    events.forEach((event) => {
      const row = extractWorker(event);

      if (row) {
        map.set(row.worker, row);
      }
    });

    return [...map.values()]
      .sort((a, b) => b.sequence - a.sequence)
      .slice(0, 12);
  }, [events]);

  return (
    <div className="rounded-2xl border border-zinc-800 bg-black p-5">
      <div className="flex items-center justify-between mb-5">
        <div>
          <div className="text-white font-semibold text-lg">Agent Activity</div>
          <div className="text-zinc-500 text-sm mt-1">live orchestration coordination</div>
        </div>

        <div className="text-emerald-400 text-sm">
          {workers.length} active
        </div>
      </div>

      <div className="space-y-3 max-h-[360px] overflow-auto pr-2">
        {workers.length === 0 && (
          <div className="text-zinc-500 text-sm">
            waiting for worker telemetry
          </div>
        )}

        {workers.map((worker) => (
          <div
            key={worker.worker}
            className="border border-zinc-800 rounded-xl p-3"
          >
            <div className="flex items-center justify-between">
              <div className="text-zinc-100 font-medium text-sm">
                {worker.worker}
              </div>

              <div className="text-xs text-cyan-400">
                seq {worker.sequence}
              </div>
            </div>

            <div className="mt-2 text-sm text-zinc-400">
              {worker.status}
            </div>

            <div className="mt-2 text-[11px] text-zinc-600 break-all">
              {worker.replayHash || "no replay hash"}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
