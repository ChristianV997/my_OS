import type { SimulationScore } from "../types";

interface Props {
  scores: SimulationScore[];
}

function ConfBar({ value, color }: { value: number; color: string }) {
  return (
    <div className="w-16 h-1.5 bg-gray-800 rounded-full overflow-hidden">
      <div
        className={`h-full rounded-full ${color}`}
        style={{ width: `${Math.min(100, value * 100).toFixed(0)}%` }}
      />
    </div>
  );
}

function roasColor(roas: number): string {
  if (roas >= 2.0) return "text-green-400";
  if (roas >= 1.2) return "text-yellow-400";
  return "text-red-400";
}

function engBadge(eng: number): string {
  if (eng >= 0.7) return "bg-green-900/50 text-green-300";
  if (eng >= 0.4) return "bg-yellow-900/50 text-yellow-300";
  return "bg-gray-800 text-gray-400";
}

function ScoreRow({ s }: { s: SimulationScore }) {
  return (
    <tr className="border-b border-gray-800/40 hover:bg-gray-800/30 text-xs">
      <td className="py-1.5 pr-2 font-bold text-gray-500 w-5">{s.rank}</td>
      <td className="py-1.5 pr-3 font-mono text-gray-200 max-w-[120px] truncate">{s.product}</td>
      <td className="py-1.5 pr-3">
        <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${engBadge(s.predicted_engagement)}`}>
          {(s.predicted_engagement * 100).toFixed(0)}%
        </span>
      </td>
      <td className={`py-1.5 pr-3 font-mono font-semibold ${roasColor(s.corrected_roas)}`}>
        {s.corrected_roas.toFixed(2)}x
      </td>
      <td className="py-1.5 pr-3 font-mono text-gray-400">
        {(s.predicted_ctr * 100).toFixed(2)}%
      </td>
      <td className="py-1.5 pr-3">
        <div className="flex flex-col gap-0.5">
          <ConfBar value={s.confidence} color="bg-blue-500" />
        </div>
      </td>
      <td className="py-1.5">
        <div className="flex flex-col gap-0.5">
          <ConfBar value={s.risk_score} color="bg-red-500" />
        </div>
      </td>
    </tr>
  );
}

export function SimulationPanel({ scores }: Props) {
  if (!scores || scores.length === 0) {
    return (
      <div className="bg-gray-900 rounded-xl p-4">
        <h2 className="text-sm font-semibold text-gray-300 mb-2 uppercase tracking-wider">
          Pre-Execution Simulation
        </h2>
        <p className="text-xs text-gray-600 italic">
          Waiting for simulation scores — model warms up after 20+ cycles…
        </p>
      </div>
    );
  }

  const top = scores[0];
  const avgConf = scores.reduce((s, r) => s + r.confidence, 0) / scores.length;
  const avgRisk = scores.reduce((s, r) => s + r.risk_score, 0) / scores.length;

  return (
    <div className="bg-gray-900 rounded-xl p-4">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">
          Pre-Execution Simulation
        </h2>
        <div className="flex gap-3 text-xs">
          <span className="text-blue-400">{scores.length} ranked</span>
          <span className="text-gray-500">
            avg conf {(avgConf * 100).toFixed(0)}%
          </span>
          <span className={avgRisk > 0.6 ? "text-red-400" : "text-gray-500"}>
            risk {(avgRisk * 100).toFixed(0)}%
          </span>
        </div>
      </div>

      {/* Top pick summary */}
      <div className="bg-gray-800/60 rounded-lg px-3 py-2 mb-3 flex items-center gap-4 text-xs">
        <span className="text-gray-500 uppercase tracking-wider text-[10px]">Top pick</span>
        <span className="font-mono text-white font-semibold">{top.product}</span>
        <span className={`font-mono font-bold ${roasColor(top.corrected_roas)}`}>
          ROAS {top.corrected_roas.toFixed(2)}x
        </span>
        {top.hook && (
          <span className="text-gray-400 truncate max-w-[160px]">hook: {top.hook}</span>
        )}
        <span className="ml-auto text-gray-500">
          rank score {(top.rank_score * 100).toFixed(0)}
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left">
          <thead>
            <tr className="text-gray-600 border-b border-gray-800 text-[10px] uppercase">
              <th className="pb-1 pr-2">#</th>
              <th className="pb-1 pr-3">Product</th>
              <th className="pb-1 pr-3">Engagement</th>
              <th className="pb-1 pr-3">ROAS est.</th>
              <th className="pb-1 pr-3">CTR est.</th>
              <th className="pb-1 pr-3">Confidence</th>
              <th className="pb-1">Risk</th>
            </tr>
          </thead>
          <tbody>
            {scores.map((s) => <ScoreRow key={`${s.product}-${s.rank}`} s={s} />)}
          </tbody>
        </table>
      </div>

      <p className="text-[10px] text-gray-700 mt-2">
        Scores computed by Ridge regression on historical outcomes. Corrected ROAS applies Bayesian calibration.
      </p>
    </div>
  );
}
