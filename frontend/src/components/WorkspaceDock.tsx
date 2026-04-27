export function WorkspaceDock() {
  const tools = [
    "Playwright Runtime",
    "Campaign Queue",
    "Telemetry Inspector",
    "Replay Console",
    "Claude Strategy",
    "Creative Intelligence",
  ];

  return (
    <div className="rounded-2xl border border-zinc-800 bg-black p-5 h-full">
      <div className="flex items-center justify-between mb-5">
        <div>
          <div className="text-white font-semibold text-lg">
            Workspace Dock
          </div>

          <div className="text-zinc-500 text-sm mt-1">
            desktop operator toolchain
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        {tools.map((tool) => (
          <button
            key={tool}
            className="rounded-xl border border-zinc-800 hover:border-cyan-500 transition p-4 text-left"
          >
            <div className="text-zinc-100 font-medium text-sm">
              {tool}
            </div>

            <div className="mt-2 text-xs text-zinc-500 leading-relaxed">
              operational workspace module
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
