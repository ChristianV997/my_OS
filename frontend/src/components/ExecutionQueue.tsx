import { useMemo } from "react";
import { useRuntimeStore } from "../runtimeStore";
import type { RuntimeEnvelope } from "../types";
import { getRuntimePriority } from "../lib/runtimePriority";

interface QueueRow {
  id: string;
  type: string;
  priority: string;
  sequence: number;
  replayHash: string;
}

function normalizeQueue(events: RuntimeEnvelope[]): QueueRow[] {
  return events.slice(-24).reverse().map((event, index) => ({
    id: `${event.sequence_id || index}-${event.type}`,
    type: String(event.type || "runtime"),
    priority: getRuntimePriority(event),
    sequence: Number(event.sequence_id || 0),
    replayHash: String(event.replay_hash || ""),
  }));
}

export function ExecutionQueue() {
  const events = useRuntimeStore((state) => state.events);
  const queue = useMemo(() => normalizeQueue(events), [events]);

  return (
    <div className="rounded-2xl border border-zinc-800 bg-black p-5 h-full">
      <div className="flex items-center justify-between mb-5">
        <div>
          <div className="text-white font-semibold text-lg">Execution Queue</div>
          <div className="text-zinc-500 text-sm mt-1">prioritized runtime operations</div>
        </div>

        <div className="text-cyan-400 text-sm">{queue.length} queued</div>
      </div>

      <div className="space-y-3 max-h-[420px] overflow-auto pr-2">
        {queue.map((item) => (
          <div key={item.id} className="rounded-xl border border-zinc-800 p-3">
            <div className="flex items-center justify-between">
              <div className="text-zinc-100 text-sm font-medium">{item.type}</div>

              <div className={`text-xs font-semibold ${
                item.priority === "critical"
                  ? "text-red-400"
                  : item.priority === "high"
                    ? "text-yellow-400"
                    : item.priority === "medium"
                      ? "text-cyan-400"
                      : "text-zinc-500"
              }`}>
                {item.priority.toUpperCase()}
              </div>
            </div>

            <div className="mt-2 text-xs text-zinc-500">sequence {item.sequence}</div>

            <div className="mt-2 text-[11px] text-zinc-600 break-all">
              {item.replayHash || "no replay hash"}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
