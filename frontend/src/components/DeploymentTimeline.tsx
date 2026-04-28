import { useMemo } from "react";

import { useRuntimeStore } from "../runtimeStore";
import type { RuntimeEnvelope } from "../types";

interface TimelineRow {
  sequence: number;
  type: string;
  replayHash: string;
  status: "success" | "fail" | "info";
}

function deriveStatus(event: RuntimeEnvelope): TimelineRow["status"] {
  const t = String(event.type || "").toLowerCase();

  if (t.includes("fail")) return "fail";
  if (t.includes("success") || t.includes("deploy") || t.includes("snapshot")) return "success";
  return "info";
}

export function DeploymentTimeline() {
  const events = useRuntimeStore((state) => state.events);

  const rows = useMemo<TimelineRow[]>(() => {
    return events
      .filter((event) => String(event.type || "").toLowerCase().includes("deploy") || String(event.type || "").toLowerCase().includes("snapshot"))
      .slice(-20)
      .map((event) => ({
        sequence: Number(event.sequence_id || 0),
        type: String(event.type || "unknown"),
        replayHash: String(event.replay_hash || ""),
        status: deriveStatus(event),
      }))
      .sort((a, b) => a.sequence - b.sequence);
  }, [events]);

  return (
    <div className="rounded-2xl border border-zinc-800 bg-black p-5">
      <div className="flex items-center justify-between mb-5">
        <div>
          <div className="text-white font-semibold text-lg">Deployment Timeline</div>
          <div className="text-zinc-500 text-sm mt-1">deterministic runtime sequence</div>
        </div>
        <div className="text-cyan-400 text-sm">{rows.length} items</div>
      </div>

      <div className="space-y-3 max-h-[360px] overflow-auto pr-2">
        {rows.length === 0 && (
          <div className="text-zinc-500 text-sm">waiting for deployment telemetry</div>
        )}

        {rows.map((row) => (
          <div key={`${row.sequence}-${row.type}`} className="border border-zinc-800 rounded-xl p-3">
            <div className="flex items-center justify-between">
              <div className="text-white text-sm font-medium">{row.type}</div>
              <div className={`text-xs ${row.status === "fail" ? "text-red-400" : row.status === "success" ? "text-emerald-400" : "text-cyan-400"}`}>
                seq {row.sequence}
              </div>
            </div>

            <div className="mt-2 text-xs text-zinc-500 break-all">
              {row.replayHash || "no replay hash"}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
