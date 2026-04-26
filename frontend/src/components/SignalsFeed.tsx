import type { Signal } from "../types";

interface Props { signals: Signal[] }

const SOURCE_BADGE: Record<string, string> = {
  amazon_bestsellers: "bg-orange-800 text-orange-200",
  tiktok_organic:     "bg-pink-800 text-pink-200",
  google_trends_v1:   "bg-blue-800 text-blue-200",
};

export function SignalsFeed({ signals }: Props) {
  return (
    <div className="bg-gray-900 rounded-xl p-4">
      <h2 className="text-sm font-semibold text-gray-300 mb-3 uppercase tracking-wider">Top Signals</h2>
      {signals.length === 0 && (
        <p className="text-xs text-gray-600 italic">Waiting for signals…</p>
      )}
      <ul className="space-y-2">
        {signals.map((s, i) => (
          <li key={i} className="flex items-center justify-between text-sm">
            <div className="flex items-center gap-2 min-w-0">
              <span
                className={`shrink-0 px-2 py-0.5 rounded text-[10px] font-bold ${SOURCE_BADGE[s.source] ?? "bg-gray-700 text-gray-300"}`}
              >
                {s.source?.replace("_", " ")}
              </span>
              <span className="truncate text-white">{s.product}</span>
            </div>
            <div className="flex items-center gap-3 shrink-0 ml-3">
              {s.velocity !== undefined && (
                <span className="text-xs text-yellow-400">↑{s.velocity.toFixed(2)}</span>
              )}
              <span className="font-mono text-green-400">{s.score.toFixed(3)}</span>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
