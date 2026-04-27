import type { Edge, Node } from "reactflow";
import type { RuntimeEnvelope } from "./types";

export interface RuntimeGraph {
  nodes: Node[];
  edges: Edge[];
}

export function buildRuntimeGraph(events: RuntimeEnvelope[]): RuntimeGraph {
  const nodes: Node[] = [];
  const edges: Edge[] = [];

  events.forEach((event, index) => {
    const nodeId = String(
      event.event_id
      || `${event.sequence_id ?? index}-${event.type}`
    );

    nodes.push({
      id: nodeId,
      position: {
        x: (index % 5) * 280,
        y: Math.floor(index / 5) * 180,
      },
      data: {
        label: `${event.type}\nseq:${event.sequence_id ?? "-"}`,
      },
      style: {
        background: "#09090b",
        border: "1px solid #27272a",
        borderRadius: 12,
        color: "#fafafa",
        width: 220,
        fontSize: 12,
      },
    });

    if (index > 0) {
      const prev = events[index - 1];

      edges.push({
        id: `${prev.event_id ?? index}-${nodeId}`,
        source: String(prev.event_id || `${prev.sequence_id}-${prev.type}`),
        target: nodeId,
        animated: true,
      });
    }
  });

  return { nodes, edges };
}
