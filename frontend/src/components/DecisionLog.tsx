import type { Decision } from "../types";

interface Props { decisions: Decision[] }

const LABEL_COLOR: Record<string, string> = {
  WINNER:  "text-green-400",
  LOSER:   "text-red-400",
  NEUTRAL: "text-gray-400",
};

export function DecisionLog({ decisions }: Props) {
  const rows = [...decisions].reverse().slice(0, 15);

  return (
    <div className="bg-gray-900 rounded-xl p-4">
      <h2 className="text-sm font-semibold text-gray-300 mb-3 uppercase tracking-wider">Recent Decisions</h2>
      {rows.length === 0 && (
        <p className="text-xs text-gray-600 italic">No decisions yet</p>
      )}
      <div className="overflow-x-auto">
        <table className="w-full text-xs text-left">
          <thead>
            <tr className="text-gray-500 border-b border-gray-800">
              <th className="pb-1 pr-3">Variant</th>
              <th className="pb-1 pr-3">ROAS</th>
              <th className="pb-1 pr-3">CTR</th>
              <th className="pb-1 pr-3">CVR</th>
              <th className="pb-1 pr-3">Regime</th>
              <th className="pb-1">Label</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((d, i) => (
              <tr key={i} className="border-b border-gray-800/50 hover:bg-gray-800/40">
                <td className="py-1 pr-3 font-mono text-gray-400">{d.variant ?? "–"}</td>
                <td className="py-1 pr-3 font-mono text-white">{d.roas?.toFixed(3) ?? "–"}</td>
                <td className="py-1 pr-3 font-mono text-gray-300">{d.ctr ? (d.ctr * 100).toFixed(2) + "%" : "–"}</td>
                <td className="py-1 pr-3 font-mono text-gray-300">{d.cvr ? (d.cvr * 100).toFixed(2) + "%" : "–"}</td>
                <td className="py-1 pr-3 text-gray-400">{d.env_regime ?? "–"}</td>
                <td className={`py-1 font-semibold ${LABEL_COLOR[d.label ?? ""] ?? "text-gray-400"}`}>
                  {d.label ?? "–"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
