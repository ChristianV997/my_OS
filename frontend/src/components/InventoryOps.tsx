import { useMemo } from "react";

import { useRuntimeStore } from "../runtimeStore";
import type { RuntimeEnvelope } from "../types";

interface InventoryRow {
  sku: string;
  velocity: number;
  inventory: number;
  roas: number;
}

function normalizeInventory(events: RuntimeEnvelope[]): InventoryRow[] {
  const rows = new Map<string, InventoryRow>();

  events.forEach((event) => {
    const payload = (event.payload || {}) as Record<string, unknown>;

    const sku = String(payload.sku || payload.product || "");

    if (!sku) return;

    const velocity = Number(payload.velocity || payload.sales || payload.conversions || 0);
    const inventory = Number(payload.inventory || payload.stock || 0);
    const roas = Number(payload.roas || payload.predicted_roas || 0);

    const existing = rows.get(sku);

    if (existing) {
      existing.velocity += velocity;
      existing.inventory = Math.max(existing.inventory, inventory);
      existing.roas = Math.max(existing.roas, roas);
      return;
    }

    rows.set(sku, {
      sku,
      velocity,
      inventory,
      roas,
    });
  });

  return [...rows.values()]
    .sort((a, b) => (b.roas + b.velocity) - (a.roas + a.velocity))
    .slice(0, 12);
}

export function InventoryOps() {
  const events = useRuntimeStore((state) => state.events);

  const inventory = useMemo(() => normalizeInventory(events), [events]);

  return (
    <div className="rounded-2xl border border-zinc-800 bg-black p-5">
      <div className="flex items-center justify-between mb-5">
        <div>
          <div className="text-white font-semibold text-lg">
            Ecommerce Operations
          </div>

          <div className="text-zinc-500 text-sm mt-1">
            inventory + scaling intelligence
          </div>
        </div>

        <div className="text-emerald-400 text-sm">
          {inventory.length} SKUs
        </div>
      </div>

      <div className="overflow-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-zinc-500 border-b border-zinc-800">
              <th className="text-left pb-3">SKU</th>
              <th className="text-right pb-3">Velocity</th>
              <th className="text-right pb-3">Inventory</th>
              <th className="text-right pb-3">ROAS</th>
            </tr>
          </thead>

          <tbody>
            {inventory.length === 0 && (
              <tr>
                <td colSpan={4} className="py-6 text-zinc-500 text-center">
                  waiting for ecommerce telemetry
                </td>
              </tr>
            )}

            {inventory.map((row) => (
              <tr
                key={row.sku}
                className="border-b border-zinc-900"
              >
                <td className="py-3 text-zinc-100">
                  {row.sku}
                </td>

                <td className="py-3 text-right text-cyan-400">
                  {row.velocity.toFixed(2)}
                </td>

                <td className="py-3 text-right text-zinc-300">
                  {row.inventory.toFixed(0)}
                </td>

                <td className="py-3 text-right text-emerald-400 font-medium">
                  {row.roas.toFixed(2)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
