import type { Edge, Node } from "reactflow";
import type { RuntimeEnvelope } from "./types";

export interface RuntimeGraph {
  nodes: Node[];
  edges: Edge[];
}

interface ClusterBucket {
  id: string;
  label: string;
  count: number;
  sequence: number;
  replayHash?: string;
}

function classifyEvent(event: RuntimeEnvelope): string {
  const type = String(event.type || "unknown").toLowerCase();

  if (type.includes("deploy")) return "deployments";
  if (type.includes("worker") || type.includes("agent")) return "agents";
  if (type.includes("snapshot") || type.includes("replay")) return "replay";
  if (type.includes("creative") || type.includes("campaign")) return "marketing";
  if (type.includes("inventory") || type.includes("product")) return "commerce";

  return "runtime";
}

function clusterEvents(events: RuntimeEnvelope[]): ClusterBucket[] {
  const buckets = new Map<string, ClusterBucket>();

  events.slice(-120).forEach((event) => {
    const cluster = classifyEvent(event);
    const replayHash = String(event.replay_hash || "");
    const key = `${cluster}:${replayHash}`;

    const existing = buckets.get(key);

    if (existing) {
      existing.count += 1;
      existing.sequence = Math.max(existing.sequence, Number(event.sequence_id || 0));
      return;
    }

    buckets.set(key, {
      id: key,
      label: cluster,
      count: 1,
      sequence: Number(event.sequence_id || 0),
      replayHash,
    });
  });

  return [...buckets.values()].sort((a, b) => a.sequence - b.sequence);
}

export function buildRuntimeGraph(events: RuntimeEnvelope[]): RuntimeGraph {
  const nodes: Node[] = [];
  const edges: Edge[] = [];

  const clusters = clusterEvents(events);

  clusters.forEach((cluster, index) => {
    const x = (index % 4) * 320;
    const y = Math.floor(index / 4) * 220;

    nodes.push({
      id: cluster.id,
      position: { x, y },
      data: {
        label: `${cluster.label}\n${cluster.count} events\nseq:${cluster.sequence}`,
      },
      style: {
        background: "#09090b",
        border: "1px solid #27272a",
        borderRadius: 14,
        color: "#fafafa",
        width: 260,
        fontSize: 12,
        padding: 12,
      },
    });

    if (index > 0) {
      const previous = clusters[index - 1];

      edges.push({
        id: `${previous.id}-${cluster.id}`,
        source: previous.id,
        target: cluster.id,
        animated: true,
      });
    }
  });

  return { nodes, edges };
}
