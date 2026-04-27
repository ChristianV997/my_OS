import { useMemo } from "react";

import { useRuntimeStore } from "../runtimeStore";

export function ReplayInspector() {
  const events = useRuntimeStore((state) => state.events);

  const replayHashes = useMemo(() => {
    const counts = new Map<string, number>();

    events.forEach((event) => {
      const hash = String(event.replay_hash || "");

      if (!hash) {
        return;
      }

      counts.set(hash, (counts.get(hash) || 0) + 1);
    });

    return [...counts.entries()]
      .map(([hash, count]) => ({ hash, count }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 8);
  }, [events]);

  return (
    <div className="rounded-2xl border border-zinc-800 bg-black p-5">
      <div className="flex items-center justify-between mb-5">
        <div>
          <div className="text-white font-semibold text-lg">
            Replay Inspector
          </div>

          <div className="text-zinc-500 text-sm mt-1">
            deterministic lineage diagnostics
          </div>
        </div>

        <div className="text-cyan-400 text-sm">
          {replayHashes.length} active
        </div>
      </div>

      <div className="space-y-3">
        {replayHashes.length === 0 && (
          <div className="text-zinc-500 text-sm">
            waiting for replay lineage
          </div>
        )}

        {replayHashes.map((item) => (
          <div
            key={item.hash}
            className="rounded-xl border border-zinc-800 p-3"
          >
            <div className="flex items-center justify-between">
              <div className="text-zinc-200 text-xs break-all max-w-[220px]">
                {item.hash}
              </div>

              <div className="text-cyan-400 text-sm font-medium">
                {item.count}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
