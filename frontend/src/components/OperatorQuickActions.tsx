interface ActionItem {
  label: string;
  description: string;
}

const ACTIONS: ActionItem[] = [
  {
    label: "Launch Creative Audit",
    description: "Run Claude marketing cognition against active creatives.",
  },
  {
    label: "Open Replay Window",
    description: "Inspect deterministic replay lineage for current runtime.",
  },
  {
    label: "Scale Winning Campaigns",
    description: "Increase budget allocation for top-performing deployments.",
  },
  {
    label: "Rebuild Runtime Graph",
    description: "Refresh orchestration clustering and telemetry hydration.",
  },
];

export function OperatorQuickActions() {
  return (
    <div className="rounded-2xl border border-zinc-800 bg-black p-5">
      <div className="flex items-center justify-between mb-5">
        <div>
          <div className="text-white font-semibold text-lg">
            Operator Quick Actions
          </div>

          <div className="text-zinc-500 text-sm mt-1">
            command center operational shortcuts
          </div>
        </div>
      </div>

      <div className="space-y-3">
        {ACTIONS.map((action) => (
          <button
            key={action.label}
            className="w-full rounded-xl border border-zinc-800 p-4 text-left hover:border-cyan-500 transition"
          >
            <div className="text-zinc-100 font-medium">
              {action.label}
            </div>

            <div className="mt-2 text-sm text-zinc-500 leading-relaxed">
              {action.description}
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
