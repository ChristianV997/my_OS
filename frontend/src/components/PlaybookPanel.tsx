import type { Playbook, Patterns } from "../types";

interface Props { playbooks: Playbook[]; patterns: Patterns }

function ConfBar({ value }: { value: number }) {
  return (
    <div className="w-full bg-gray-700 rounded-full h-1.5 mt-1">
      <div
        className="bg-green-400 h-1.5 rounded-full"
        style={{ width: `${Math.min(value * 100, 100).toFixed(0)}%` }}
      />
    </div>
  );
}

export function PlaybookPanel({ playbooks, patterns }: Props) {
  const topHooks = patterns?.top_hooks ?? [];

  return (
    <div className="bg-gray-900 rounded-xl p-4 space-y-4">
      <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">Playbooks</h2>

      {playbooks.length === 0 && (
        <p className="text-xs text-gray-600 italic">No playbooks yet — run cycles to build patterns</p>
      )}

      {playbooks.map((pb) => (
        <div key={`${pb.product}-${pb.phase}`} className="border border-gray-800 rounded-lg p-3 space-y-2">
          <div className="flex justify-between items-center">
            <span className="font-semibold text-white text-sm">{pb.product}</span>
            <span className="text-xs text-gray-400">{pb.phase}</span>
          </div>
          <div className="text-xs text-gray-400">
            ROAS est. <span className="text-green-400 font-mono">{pb.estimated_roas.toFixed(2)}</span> ·{" "}
            {pb.evidence_count} samples
          </div>
          <ConfBar value={pb.confidence} />
          {pb.top_hooks.length > 0 && (
            <div className="text-xs text-gray-300">
              <span className="text-gray-500">Hooks: </span>
              {pb.top_hooks.slice(0, 2).join(" · ")}
            </div>
          )}
        </div>
      ))}

      {topHooks.length > 0 && (
        <div>
          <h3 className="text-xs text-gray-500 uppercase mb-1">Top Performing Hooks</h3>
          <ol className="space-y-1">
            {topHooks.slice(0, 5).map((h, i) => (
              <li key={i} className="text-xs text-gray-300 flex gap-2">
                <span className="text-gray-600">{i + 1}.</span> {h}
              </li>
            ))}
          </ol>
        </div>
      )}
    </div>
  );
}
