import type { RuntimeEnvelope } from "../types";

export type RuntimePriority = "critical" | "high" | "medium" | "low";

export function getRuntimePriority(event: RuntimeEnvelope): RuntimePriority {
  const type = String(event.type || "").toLowerCase();

  if (type.includes("fail") || type.includes("divergence")) {
    return "critical";
  }

  if (type.includes("deploy") || type.includes("snapshot") || type.includes("campaign")) {
    return "high";
  }

  if (type.includes("worker") || type.includes("agent") || type.includes("inventory")) {
    return "medium";
  }

  return "low";
}

const PRIORITY_WEIGHT: Record<RuntimePriority, number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
};

export function sortRuntimeEvents(events: RuntimeEnvelope[]): RuntimeEnvelope[] {
  return [...events].sort((a, b) => {
    const pa = PRIORITY_WEIGHT[getRuntimePriority(a)];
    const pb = PRIORITY_WEIGHT[getRuntimePriority(b)];

    if (pa !== pb) {
      return pa - pb;
    }

    const sa = typeof a.sequence_id === "number" ? a.sequence_id : Number.MAX_SAFE_INTEGER;
    const sb = typeof b.sequence_id === "number" ? b.sequence_id : Number.MAX_SAFE_INTEGER;

    if (sa !== sb) {
      return sa - sb;
    }

    const ta = Number(a.ts || 0);
    const tb = Number(b.ts || 0);

    return ta - tb;
  });
}
