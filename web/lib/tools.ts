/**
 * Client tools dispatched by the ByteVoice Bangla Receptionist during live call.
 * Matches bytevoice.voice.persona TOOL_SPECS.
 */

import { callTool } from "./api";

export const TOOL_NAMES = [
  "get_clinic_info",
  "check_availability",
  "book_appointment",
  "request_callback",
] as const;

export type ToolName = (typeof TOOL_NAMES)[number];

export type ToolLogEntry = { name: string; at: number; result?: unknown };

/**
 * Build clientTools map for ElevenLabs useConversation hook.
 */
export function buildClientTools(onCall: (entry: ToolLogEntry) => void) {
  const tools: Record<string, (parameters: Record<string, unknown>) => Promise<string>> = {};
  for (const name of TOOL_NAMES) {
    tools[name] = async (parameters: Record<string, unknown>) => {
      onCall({ name, at: Date.now() });
      const result = await callTool(name, parameters ?? {});
      return JSON.stringify(result);
    };
  }
  return tools;
}
