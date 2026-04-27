import { create } from "zustand";
import type { RuntimeEnvelope } from "./types";

interface RuntimeStoreState {
  events: RuntimeEnvelope[];
  append: (event: RuntimeEnvelope) => void;
  clear: () => void;
}

const MAX_EVENTS = 500;

export const useRuntimeStore = create<RuntimeStoreState>((set) => ({
  events: [],
  append: (event) => set((state) => ({
    events: [...state.events, event].slice(-MAX_EVENTS),
  })),
  clear: () => set({ events: [] }),
}));
