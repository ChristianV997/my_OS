import type { RuntimeSnapshot } from "../types";

interface Props {
  snapshot: RuntimeSnapshot | null;
  lastWorker: { name: string; ts: number } | null;
  connected: boolean;
}

function Row({ label, value, accent }: { label: string; value: string; accent?: string }) {
  return (
    <div className="flex justify-between text-sm py-1 border-b border-gray-800/50">
      <span className="text-gray-400">{label}</span>
      <span className={`font-mono ${accent ?? "text-white"}`}>{value}</span>
    </div>
  );
}

export function AgentStatus({ snapshot, lastWorker, connected }: Props) {
  const age = lastWorker ? Math.round((Date.now() / 1000 - lastWorker.ts)) : null;

  return (
    <div className="bg-gray-900 rounded-xl p-4">
      <h2 className="text-sm font-semibold text-gray-300 mb-3 uppercase tracking-wider">Agent Status</h2>
      <Row label="WebSocket" value={connected ? "connected" : "reconnecting"} accent={connected ? "text-green-400" : "text-red-400"} />
      <Row label="Phase" value={snapshot?.phase ?? "–"} />
      <Row label="Regime" value={snapshot?.regime ?? "–"} />
      <Row label="Cycles" value={snapshot ? String(snapshot.cycle) : "–"} />
      <Row label="Signals ingested" value={snapshot ? String(snapshot.signal_count) : "–"} />
      <Row label="Active playbooks" value={snapshot ? String(snapshot.top_playbooks.length) : "–"} />
      {lastWorker && (
        <Row
          label={`Last: ${lastWorker.name.replace("_run_", "")}`}
          value={age !== null ? `${age}s ago` : "–"}
          accent="text-yellow-400"
        />
      )}
    </div>
  );
}
