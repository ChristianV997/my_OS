import { create } from "zustand";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type AnyData = any;

interface WsState {
  connected: boolean;
  snapshot: AnyData | null;
  capitalHistory: [number, number][];
  roasHistory: [number, number][];
  lastWorker: string | null;
  taskInventory: AnyData | null;
  setConnected: (v: boolean) => void;
  handleMessage: (msg: AnyData) => void;
}

export const useWsStore = create<WsState>((set) => ({
  connected: false,
  snapshot: null,
  capitalHistory: [],
  roasHistory: [],
  lastWorker: null,
  taskInventory: null,

  setConnected: (connected) => set({ connected }),

  handleMessage: (msg) =>
    set((s) => {
      switch (msg.type) {
        case "snapshot":
          return { snapshot: msg.data };
        case "tick": {
          const ts = Date.now();
          const capital = msg.data?.capital ?? 0;
          const roas    = msg.data?.avg_roas ?? 0;
          return {
            capitalHistory: [...s.capitalHistory.slice(-199), [ts, capital]] as [number, number][],
            roasHistory:    [...s.roasHistory.slice(-199),    [ts, roas]]    as [number, number][],
          };
        }
        case "worker":
          return { lastWorker: msg.data?.worker_id ?? msg.data?.name ?? msg.data?.phase ?? "worker" };
        case "task_inventory":
          return { taskInventory: msg.data };
        default:
          return {};
      }
    }),
}));
