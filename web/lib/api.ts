/**
 * Typed API client for ByteVoice FastAPI backend.
 * Handles voice session tokens, tool calls, and data portal CRUD.
 */

const BASE = process.env.NEXT_PUBLIC_API_BASE ?? "";

export type Config = {
  voice_ok: boolean;
  voice_hint: string;
  clinic_name: string;
  has_agent: boolean;
};

export type SessionStart = {
  token: string;
  first_message: string;
};

export type TranscriptTurn = {
  speaker: "ai" | "patient" | "system";
  text_bn: string;
  text_en?: string;
  ts?: string;
};

export type CallExtraction = {
  reason_for_visit?: string;
  preferred_datetime?: string;
  intent?: string;
  urgency?: string;
  notes?: string;
};

export type CallSummary = {
  id: string;
  caller_name: string;
  caller_phone: string;
  started_at: string;
  duration_s: number;
  status: "in_progress" | "booked" | "enquiry" | "follow_up_needed" | "incomplete" | "failed";
  summary: string;
};

export type CallDetail = CallSummary & {
  ended_at?: string;
  recording_url?: string;
  transcripts: TranscriptTurn[];
  extraction?: CallExtraction;
  appointments: {
    id: number;
    slot: string;
    doctor: string;
    service: string;
    status: string;
  }[];
};

export type AppointmentItem = {
  id: number;
  patient_name: string;
  patient_phone: string;
  slot_datetime: string;
  service_name: string;
  doctor_name: string;
  status: string;
  notes?: string;
  created_at: string;
};

export type CallbackItem = {
  id: number;
  patient_name: string;
  patient_phone: string;
  reason: string;
  status: "pending" | "contacted" | "resolved";
  created_at: string;
};

export type PortalStats = {
  total_calls: number;
  booked_calls: number;
  enquiry_calls: number;
  follow_up_calls: number;
  total_appointments: number;
  pending_callbacks: number;
};

async function fetchJson<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE}${path}`, options);
  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `${path} failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export const getConfig = () => fetchJson<Config>("/api/config");

/** Mint a short-lived conversation token for the ElevenLabs WebRTC session. */
export async function getSessionStart(): Promise<SessionStart> {
  return fetchJson<SessionStart>("/api/voice/token", { method: "POST" });
}

/** Execute a client tool in the Python backend. */
export async function callTool(name: string, parameters: Record<string, unknown>): Promise<unknown> {
  try {
    return await fetchJson(`/api/tools/${name}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(parameters ?? {}),
    });
  } catch (err: unknown) {
    return { error: (err as Error).message };
  }
}

/** Finalize call session when call drops or hangs up. */
export async function completeCall(payload: {
  id?: string;
  duration_s: number;
  status: string;
  summary?: string;
  transcripts: TranscriptTurn[];
  extraction?: CallExtraction;
}) {
  return fetchJson("/api/voice/complete", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

/** Portal Login */
export async function loginPortal(username: string, password: string) {
  return fetchJson<{ access_token: string; username: string; role: string }>("/api/portal/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
}

/** Portal Dashboard APIs */
export const getPortalStats = () => fetchJson<PortalStats>("/api/portal/stats");

export async function getPortalCalls(skip = 0, limit = 50, status?: string, search?: string) {
  const params = new URLSearchParams({ skip: String(skip), limit: String(limit) });
  if (status && status !== "all") params.append("status", status);
  if (search) params.append("search", search);
  return fetchJson<{ total: number; calls: CallSummary[] }>(`/api/portal/calls?${params}`);
}

export const getPortalCallDetail = (id: string) => fetchJson<CallDetail>(`/api/portal/calls/${id}`);

export const getPortalAppointments = () => fetchJson<{ total: number; appointments: AppointmentItem[] }>("/api/portal/appointments");

export const getPortalCallbacks = () => fetchJson<CallbackItem[]>("/api/portal/callbacks");

export const getClinicInfo = () => fetchJson<Record<string, unknown>>("/api/portal/clinic");
