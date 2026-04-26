import type { RuntimeSnapshot } from "../types";

const PHASE_COLORS: Record<string, string> = {
  RESEARCH: "bg-blue-600",
  EXPLORE:  "bg-yellow-500",
  VALIDATE: "bg-orange-500",
  SCALE:    "bg-green-500",
};

interface Props { snapshot: RuntimeSnapshot | null; connected: boolean }

export function PhaseHeader({ snapshot, connected }: Props) {
  const phase = snapshot?.phase ?? "–";
  const bg = PHASE_COLORS[phase] ?? "bg-gray-600";

  return (
    <div className="flex items-center justify-between px-6 py-3 bg-gray-900 border-b border-gray-800">
      <div className="flex items-center gap-4">
        <span className="text-xl font-bold tracking-tight text-white">MarketOS</span>
        <span className={`px-3 py-1 rounded-full text-xs font-bold text-white ${bg}`}>{phase}</span>
        <span className="text-sm text-gray-400">
          Cycle <span className="text-white font-mono">{snapshot?.cycle ?? "–"}</span>
        </span>
        <span className="text-sm text-gray-400">
          Regime <span className="text-white">{snapshot?.regime ?? "–"}</span>
        </span>
      </div>
      <div className="flex items-center gap-2">
        <div className={`w-2 h-2 rounded-full ${connected ? "bg-green-400 animate-pulse" : "bg-red-500"}`} />
        <span className="text-xs text-gray-400">{connected ? "live" : "reconnecting"}</span>
      </div>
    </div>
  );
}
