import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";

const BASE = (import.meta.env.VITE_API_URL as string) ?? "";

async function get<T>(path: string): Promise<T> {
  const r = await fetch(`${BASE}${path}`);
  if (!r.ok) throw new Error(`${r.status} ${path}`);
  return r.json() as T;
}

async function post<T>(path: string, body?: unknown): Promise<T> {
  const r = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body != null ? JSON.stringify(body) : undefined,
  });
  if (!r.ok) throw new Error(`${r.status} ${path}`);
  return r.json() as T;
}

const FAST = 5_000;
const MED  = 15_000;
const SLOW = 60_000;

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type AnyData = any;

export const useMetricsData       = () => useQuery<AnyData>({ queryKey: ["metrics"],            queryFn: () => get("/metrics"),                         refetchInterval: FAST });
export const useSnapshot          = () => useQuery<AnyData>({ queryKey: ["snapshot"],           queryFn: () => get("/snapshot"),                        refetchInterval: FAST });
export const useOpportunities     = () => useQuery<AnyData>({ queryKey: ["opportunities"],      queryFn: () => get("/opportunities?limit=30"),           refetchInterval: MED  });
export const useCampaigns         = () => useQuery<AnyData>({ queryKey: ["campaigns"],          queryFn: () => get("/campaigns"),                       refetchInterval: MED  });
export const useCreatives         = () => useQuery<AnyData>({ queryKey: ["creatives"],          queryFn: () => get("/creatives"),                       refetchInterval: MED  });
export const useGeo               = () => useQuery<AnyData>({ queryKey: ["geo"],                queryFn: () => get("/geo"),                             refetchInterval: MED  });
export const useAlerts            = () => useQuery<AnyData>({ queryKey: ["alerts"],             queryFn: () => get("/alerts"),                          refetchInterval: FAST });
export const useRisk              = () => useQuery<AnyData>({ queryKey: ["risk"],               queryFn: () => get("/risk"),                            refetchInterval: MED  });
export const useRiskStatus        = () => useQuery<AnyData>({ queryKey: ["risk_status"],        queryFn: () => get("/risk/status"),                     refetchInterval: FAST });
export const useAgents            = () => useQuery<AnyData>({ queryKey: ["agents"],             queryFn: () => get("/agents"),                          refetchInterval: MED  });
export const useRuntimeTasks      = () => useQuery<AnyData>({ queryKey: ["runtime_tasks"],      queryFn: () => get("/runtime/tasks"),                   refetchInterval: FAST });
export const useEvents            = (limit = 200) => useQuery<AnyData>({ queryKey: ["events", limit], queryFn: () => get(`/events?limit=${limit}`),    refetchInterval: FAST });
export const usePredictionErrors  = () => useQuery<AnyData>({ queryKey: ["pred_errors"],        queryFn: () => get("/prediction_errors?limit=100"),     refetchInterval: MED  });
export const useCalibration       = () => useQuery<AnyData>({ queryKey: ["calibration"],        queryFn: () => get("/simulation/calibration"),          refetchInterval: SLOW });
export const useSimulationScores  = () => useQuery<AnyData>({ queryKey: ["sim_scores"],         queryFn: () => get("/simulation/scores?limit=20"),      refetchInterval: MED  });
export const usePlaybook          = () => useQuery<AnyData>({ queryKey: ["playbook"],           queryFn: () => get("/playbook"),                        refetchInterval: MED  });
export const usePortfolio         = () => useQuery<AnyData>({ queryKey: ["portfolio"],          queryFn: () => get("/portfolio"),                       refetchInterval: MED  });
export const useCapitalAllocation = () => useQuery<AnyData>({ queryKey: ["capital_allocation"], queryFn: () => get("/capital_allocation"),              refetchInterval: MED  });
export const useMacro             = () => useQuery<AnyData>({ queryKey: ["macro"],              queryFn: () => get("/macro"),                           refetchInterval: SLOW });
export const useCausal            = () => useQuery<AnyData>({ queryKey: ["causal"],             queryFn: () => get("/causal"),                          refetchInterval: SLOW });
export const useAccounts          = () => useQuery<AnyData>({ queryKey: ["accounts"],           queryFn: () => get("/accounts"),                        refetchInterval: MED  });
export const usePhase             = () => useQuery<AnyData>({ queryKey: ["phase"],              queryFn: () => get("/phase"),                           refetchInterval: MED  });
export const useBandit            = () => useQuery<AnyData>({ queryKey: ["bandit"],             queryFn: () => get("/bandit"),                          refetchInterval: SLOW });

export function useTriggerCycle() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: () => post("/cycle"), onSuccess: () => qc.invalidateQueries() });
}
export function usePauseRunner() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: () => post("/runner/pause"), onSuccess: () => qc.invalidateQueries({ queryKey: ["snapshot"] }) });
}
export function useResumeRunner() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: () => post("/runner/resume"), onSuccess: () => qc.invalidateQueries({ queryKey: ["snapshot"] }) });
}
export function useActivateKillSwitch() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: (reason: string) => post("/risk/killswitch/activate", { reason }), onSuccess: () => qc.invalidateQueries() });
}
export function useDeactivateKillSwitch() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: () => post("/risk/killswitch/deactivate"), onSuccess: () => qc.invalidateQueries() });
}
export function useCampaignOverride() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: ({ id, action }: { id: string; action: string }) => post(`/campaigns/${id}/override`, { action }), onSuccess: () => qc.invalidateQueries({ queryKey: ["campaigns"] }) });
}
export function useTikTokLaunch() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: () => post("/tiktok/launch"), onSuccess: () => qc.invalidateQueries() });
}
