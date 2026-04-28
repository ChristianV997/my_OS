interface StrategyItem {
  title: string;
  summary: string;
  priority: "HIGH" | "MEDIUM" | "LOW";
}

const STRATEGIES: StrategyItem[] = [
  {
    title: "Scale Winning Hooks",
    summary: "Claude detected strong engagement velocity in short-form curiosity hooks. Increase deployment allocation for top ROAS creatives.",
    priority: "HIGH",
  },
  {
    title: "Creative Fatigue Risk",
    summary: "Repeated ad variants are converging in CTR. Introduce new visual angles before deployment decay accelerates.",
    priority: "MEDIUM",
  },
  {
    title: "Bundle Opportunity",
    summary: "Cross-sell inventory clusters around wellness and productivity categories show strong reinforcement overlap.",
    priority: "LOW",
  },
];

export function ClaudeStrategyFeed() {
  return (
    <div className="rounded-2xl border border-zinc-800 bg-black p-5">
      <div className="flex items-center justify-between mb-5">
        <div>
          <div className="text-white font-semibold text-lg">
            Claude Strategic Intelligence
          </div>

          <div className="text-zinc-500 text-sm mt-1">
            marketing cognition + strategic synthesis
          </div>
        </div>

        <div className="text-purple-400 text-sm">
          cognition active
        </div>
      </div>

      <div className="space-y-4">
        {STRATEGIES.map((item) => (
          <div
            key={item.title}
            className="rounded-xl border border-zinc-800 p-4"
          >
            <div className="flex items-center justify-between">
              <div className="text-zinc-100 font-medium">
                {item.title}
              </div>

              <div className={`text-xs font-semibold ${
                item.priority === "HIGH"
                  ? "text-red-400"
                  : item.priority === "MEDIUM"
                    ? "text-yellow-400"
                    : "text-emerald-400"
              }`}>
                {item.priority}
              </div>
            </div>

            <div className="mt-3 text-sm text-zinc-400 leading-relaxed">
              {item.summary}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
