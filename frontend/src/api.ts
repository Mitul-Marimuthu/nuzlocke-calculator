import axios from "axios";
import type { DisplayData } from "./types";

const BASE = "";  // same origin via Vite proxy

export async function createSession(): Promise<string> {
  const { data } = await axios.post(`${BASE}/session`);
  return data.session_id;
}

export async function uploadSav(sessionId: string, file: File) {
  const form = new FormData();
  form.append("file", file);
  const { data } = await axios.post(`${BASE}/session/${sessionId}/upload/sav`, form);
  return data;
}

export async function uploadGba(sessionId: string, file: File, trainerHint?: string) {
  const form = new FormData();
  form.append("file", file);
  if (trainerHint) form.append("trainer_hint", trainerHint);
  const { data } = await axios.post(`${BASE}/session/${sessionId}/upload/gba`, form);
  return data;
}

export async function analyze(sessionId: string): Promise<DisplayData> {
  const { data } = await axios.post(`${BASE}/session/${sessionId}/analyze`);
  return data.display_data;
}
