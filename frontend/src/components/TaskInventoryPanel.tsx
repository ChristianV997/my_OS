import type { TaskInventory, TaskRecord } from "../types";

interface Props { inventory: TaskInventory | null }

const KIND_ICON: Record<string, string> = {
  thread:       "🧵",
  loop:         "🔄",
  celery:       "🌿",
  scheduler:    "🗓",
  ws:           "⚡",
  queue:        "📬",
  state_writer: "✍️",
  unknown:      "❓",
};

const STATUS_COLOR: Record<string, string> = {
  ok:      "text-green-400",
  error:   "text-red-400",
  idle:    "text-gray-500",
  paused:  "text-yellow-400",
  skipped: "text-gray-400",
  unknown: "text-gray-600",
};

function TaskRow({ t }: { t: TaskRecord }) {
  const icon = KIND_ICON[t.kind] ?? "❓";
  const statusCls = STATUS_COLOR[t.last_status] ?? "text-gray-500";
  const staleCls = !t.active && t.last_run_ts ? "opacity-40" : "";
  const unconfiguredCls = !t.configured ? "opacity-30" : "";

  return (
    <tr className={`border-b border-gray-800/40 hover:bg-gray-800/30 text-xs ${staleCls} ${unconfiguredCls}`}>
      <td className="py-1 pr-2 whitespace-nowrap">{icon}</td>
      <td className="py-1 pr-3 font-mono text-gray-200 max-w-[160px] truncate">{t.name}</td>
      <td className="py-1 pr-3 text-gray-400 hidden lg:table-cell max-w-[240px] truncate">{t.description}</td>
      <td className="py-1 pr-3">
        <span className={`font-semibold ${statusCls}`}>{t.last_status}</span>
      </td>
      <td className="py-1 pr-3 font-mono text-gray-400">
        {t.interval_s != null ? `${t.interval_s}s` : "event"}
      </td>
      <td className="py-1 font-mono text-gray-500">
        {t.age_s != null ? `${t.age_s}s ago` : t.configured ? "never" : "unconfigured"}
      </td>
    </tr>
  );
}

export function TaskInventoryPanel({ inventory }: Props) {
  if (!inventory) {
    return (
      <div className="bg-gray-900 rounded-xl p-4">
        <h2 className="text-sm font-semibold text-gray-300 mb-2 uppercase tracking-wider">
          Runtime Task Inventory
        </h2>
        <p className="text-xs text-gray-600 italic">Waiting for inventory heartbeat (30s interval)…</p>
      </div>
    );
  }

  const { summary, tasks } = inventory;
  const byKind = Object.entries(summary.by_kind).sort((a, b) => a[0].localeCompare(b[0]));

  return (
    <div className="bg-gray-900 rounded-xl p-4">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">
          Runtime Task Inventory
        </h2>
        <div className="flex gap-3 text-xs">
          <span className="text-green-400">{summary.active} active</span>
          <span className="text-gray-500">{summary.idle} idle</span>
          {summary.unconfigured > 0 && (
            <span className="text-yellow-500">{summary.unconfigured} unconfigured</span>
          )}
        </div>
      </div>

      {/* Kind summary badges */}
      <div className="flex flex-wrap gap-2 mb-3">
        {byKind.map(([kind, count]) => (
          <span key={kind} className="px-2 py-0.5 bg-gray-800 rounded text-[10px] text-gray-400">
            {KIND_ICON[kind]} {kind} ({count})
          </span>
        ))}
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left">
          <thead>
            <tr className="text-gray-600 border-b border-gray-800 text-[10px] uppercase">
              <th className="pb-1 pr-2" />
              <th className="pb-1 pr-3">Name</th>
              <th className="pb-1 pr-3 hidden lg:table-cell">Description</th>
              <th className="pb-1 pr-3">Status</th>
              <th className="pb-1 pr-3">Interval</th>
              <th className="pb-1">Last run</th>
            </tr>
          </thead>
          <tbody>
            {tasks.map((t) => <TaskRow key={t.name} t={t} />)}
          </tbody>
        </table>
      </div>
    </div>
  );
}
