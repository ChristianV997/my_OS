import type { RuntimeSnapshot } from "../types";
import { AreaChart, Area, Tooltip, ResponsiveContainer } from "recharts";

interface Props {
  snapshot: RuntimeSnapshot | null;
  capitalHistory: { t: number; v: number }[];
  roasHistory: { t: number; v: number }[];
}

function Stat({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="bg-gray-900 rounded-xl p-4 flex flex-col gap-1">
      <span className="text-xs text-gray-500 uppercase tracking-wider">{label}</span>
      <span className="text-2xl font-bold font-mono text-white">{value}</span>
      {sub && <span className="text-xs text-gray-400">{sub}</span>}
    </div>
  );
}

function MiniChart({ data, color }: { data: { t: number; v: number }[]; color: string }) {
  return (
    <ResponsiveContainer width="100%" height={60}>
      <AreaChart data={data} margin={{ top: 4, right: 0, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id={`grad-${color}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor={color} stopOpacity={0.3} />
            <stop offset="95%" stopColor={color} stopOpacity={0} />
          </linearGradient>
        </defs>
        <Tooltip
          contentStyle={{ background: "#1f2937", border: "none", fontSize: 11 }}
          formatter={(v: number) => v.toFixed(4)}
        />
        <Area type="monotone" dataKey="v" stroke={color} fill={`url(#grad-${color})`} dot={false} strokeWidth={1.5} />
      </AreaChart>
    </ResponsiveContainer>
  );
}

export function MetricsGrid({ snapshot, capitalHistory, roasHistory }: Props) {
  const snap = snapshot;
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 p-4">
      <Stat
        label="Capital"
        value={snap ? `$${snap.capital.toLocaleString()}` : "–"}
        sub="current portfolio value"
      />
      <Stat
        label="Avg ROAS"
        value={snap ? snap.avg_roas.toFixed(3) : "–"}
        sub="last 20 cycles"
      />
      <Stat
        label="Win Rate"
        value={snap ? `${(snap.win_rate * 100).toFixed(1)}%` : "–"}
        sub="ROAS ≥ 1.5"
      />
      <Stat
        label="Signals"
        value={snap ? String(snap.signal_count) : "–"}
        sub="total ingested"
      />

      <div className="bg-gray-900 rounded-xl p-4 col-span-2">
        <span className="text-xs text-gray-500 uppercase tracking-wider">Capital Curve</span>
        <MiniChart data={capitalHistory} color="#34d399" />
      </div>
      <div className="bg-gray-900 rounded-xl p-4 col-span-2">
        <span className="text-xs text-gray-500 uppercase tracking-wider">ROAS Trend</span>
        <MiniChart data={roasHistory} color="#60a5fa" />
      </div>
    </div>
  );
}
