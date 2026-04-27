import "./index.css";
import { useState } from "react";
import { useMetrics } from "./hooks/useMetrics";
import { PhaseHeader } from "./components/PhaseHeader";
import { MetricsGrid } from "./components/MetricsGrid";
import { SignalsFeed } from "./components/SignalsFeed";
import { PlaybookPanel } from "./components/PlaybookPanel";
import { DecisionLog } from "./components/DecisionLog";
import { AgentStatus } from "./components/AgentStatus";
import { TaskInventoryPanel } from "./components/TaskInventoryPanel";
import { SimulationPanel } from "./components/SimulationPanel";
import { CommandCenter } from "./components/CommandCenter";

const TABS = ["Command Center", "Overview", "Simulation", "Tasks"] as const;
type Tab = typeof TABS[number];

export default function App() {
  const {
    snapshot,
    capitalHistory,
    roasHistory,
    lastWorker,
    taskInventory,
    connected,
  } = useMetrics();

  const [tab, setTab] = useState<Tab>("Command Center");

  return (
    <div className="min-h-screen bg-gray-950 flex flex-col">
      <PhaseHeader snapshot={snapshot} connected={connected} />

      <div className="flex gap-1 px-4 pt-3 border-b border-gray-800 overflow-auto">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm rounded-t font-medium whitespace-nowrap transition-colors ${
              tab === t
                ? "bg-gray-900 text-white border border-b-transparent border-gray-800"
                : "text-gray-500 hover:text-gray-300"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      <main className="flex-1 p-4">
        {tab === "Command Center" && (
          <CommandCenter snapshot={snapshot} connected={connected} />
        )}

        {tab === "Overview" && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <div className="lg:col-span-2 space-y-4">
              <MetricsGrid
                snapshot={snapshot}
                capitalHistory={capitalHistory}
                roasHistory={roasHistory}
              />

              <DecisionLog decisions={snapshot?.recent_decisions ?? []} />
            </div>

            <div className="space-y-4">
              <AgentStatus snapshot={snapshot} lastWorker={lastWorker} connected={connected} />
              <SignalsFeed signals={snapshot?.top_signals ?? []} />
              <PlaybookPanel
                playbooks={snapshot?.top_playbooks ?? []}
                patterns={snapshot?.patterns ?? {
                  hook_scores: {},
                  angle_scores: {},
                  regime_scores: {},
                  top_hooks: [],
                  top_angles: [],
                }}
              />
            </div>
          </div>
        )}

        {tab === "Simulation" && (
          <div className="max-w-6xl mx-auto space-y-4">
            <SimulationPanel scores={snapshot?.simulation_scores ?? []} />
          </div>
        )}

        {tab === "Tasks" && (
          <div className="max-w-6xl mx-auto">
            <TaskInventoryPanel inventory={taskInventory} />
          </div>
        )}
      </main>
    </div>
  );
}
