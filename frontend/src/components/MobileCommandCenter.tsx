import { useMemo, useState } from "react";

import { useRuntimeStore } from "../runtimeStore";
import type { RuntimeEnvelope, RuntimeSnapshot } from "../types";

interface Props {
  snapshot: RuntimeSnapshot | null;
  connected: boolean;
}

function isDeployment(event: RuntimeEnvelope): boolean {
  const type = String(event.type || "").toLowerCase();
  return type.includes("deploy") || type.includes("snapshot");
}

function isFailure(event: RuntimeEnvelope): boolean {
  return String(event.type || "").toLowerCase().includes("fail");
}

export function MobileCommandCenter({ snapshot, connected }: Props) {
  const events = useRuntimeStore((state) => state.events);
  const [busy, setBusy] = useState(false);

  const summary = useMemo(() => {
    const deployments = events.filter(isDeployment).length;
    const failures = events.filter(isFailure).length;
    const latest = events[events.length - 1];

    return {
      deployments,
      failures,
      latest,
      replayHashes: new Set(events.map((event) => event.replay_hash).filter(Boolean)).size,
    };
  }, [events]);

  const sendControl = async (endpoint: string) => {
    try {
      setBusy(true);
      await fetch(endpoint, { method: "POST" });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-4 xl:hidden">
      <div className="rounded-2xl border border-zinc-800 bg-black p-4">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-white text-xl font-semibold">
              my_OS
            </div>
            <div className="text-zinc-500 text-sm mt-1">
              mobile operator cockpit
            </div>
          </div>

          <div className={`px-3 py-1 rounded-full text-xs font-semibold ${connected ? "bg-emerald-500/20 text-emerald-400" : "bg-red-500/20 text-red-400"}`}>
            {connected ? "LIVE" : "OFFLINE"}
          </div>
        </div>

        <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
          <div className="rounded-xl border border-zinc-800 p-3">
            <div className="text-zinc-500 text-xs">Phase</div>
            <div className="text-white mt-1">{snapshot?.phase || "UNKNOWN"}</div>
          </div>

          <div className="rounded-xl border border-zinc-800 p-3">
            <div className="text-zinc-500 text-xs">Capital</div>
            <div className="text-emerald-400 mt-1">${Number(snapshot?.capital || 0).toFixed(0)}</div>
          </div>

          <div className="rounded-xl border border-zinc-800 p-3">
            <div className="text-zinc-500 text-xs">Deployments</div>
            <div className="text-white mt-1">{summary.deployments}</div>
          </div>

          <div className="rounded-xl border border-zinc-800 p-3">
            <div className="text-zinc-500 text-xs">Hashes</div>
            <div className="text-cyan-400 mt-1">{summary.replayHashes}</div>
          </div>
        </div>

        <div className="mt-4 grid grid-cols-2 gap-3">
          <button
            disabled={busy}
            onClick={() => sendControl("/runner/resume")}
            className="rounded-xl bg-emerald-500 px-3 py-3 text-black font-semibold"
          >
            Resume
          </button>

          <button
            disabled={busy}
            onClick={() => sendControl("/runner/pause")}
            className="rounded-xl bg-yellow-500 px-3 py-3 text-black font-semibold"
          >
            Pause
          </button>
        </div>
      </div>

      <details className="rounded-2xl border border-zinc-800 bg-black p-4" open>
        <summary className="cursor-pointer text-white font-semibold">
          Live runtime
        </summary>
        <div className="mt-3 text-sm text-zinc-400 break-all">
          {summary.latest
            ? `${summary.latest.type} · seq ${summary.latest.sequence_id ?? "-"}`
            : "Waiting for telemetry"}
        </div>
      </details>

      <details className="rounded-2xl border border-zinc-800 bg-black p-4">
        <summary className="cursor-pointer text-white font-semibold">
          Replay lineage
        </summary>
        <div className="mt-3 text-sm text-zinc-500 break-all">
          {summary.latest?.replay_hash || "Waiting for replay hash"}
        </div>
      </details>

      <details className="rounded-2xl border border-zinc-800 bg-black p-4">
        <summary className="cursor-pointer text-white font-semibold">
          Delivery health
        </summary>
        <div className="mt-3 text-sm text-zinc-400">
          failures: {summary.failures}
        </div>
        <div className="mt-1 text-sm text-zinc-400">
          ROAS: {Number(snapshot?.avg_roas || 0).toFixed(2)}
        </div>
      </details>

      <details className="rounded-2xl border border-zinc-800 bg-black p-4">
        <summary className="cursor-pointer text-white font-semibold">
          Quick controls
        </summary>
        <div className="mt-3 grid grid-cols-1 gap-2">
          <button
            disabled={busy}
            onClick={() => sendControl("/cycle")}
            className="rounded-xl border border-cyan-500 px-3 py-3 text-cyan-400 font-semibold"
          >
            Run cycle
          </button>

          <button
            disabled={busy}
            onClick={() => sendControl("/runner/resume")}
            className="rounded-xl border border-zinc-700 px-3 py-3 text-zinc-200 font-semibold"
          >
            Sync workspace
          </button>
        </div>
      </details>
    </div>
  );
}
