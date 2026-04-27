import { ExecutionQueue } from "./ExecutionQueue";
import { WorkspaceDock } from "./WorkspaceDock";

export function DesktopWorkspace() {
  return (
    <div className="hidden 2xl:grid grid-cols-12 gap-6">
      <div className="col-span-8">
        <ExecutionQueue />
      </div>

      <div className="col-span-4">
        <WorkspaceDock />
      </div>
    </div>
  );
}
