export const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export type ProjectStatus =
  | "uploaded"
  | "recognizing"
  | "recognized"
  | "analyzing"
  | "analyzed"
  | "reporting"
  | "completed"
  | "failed";

export type RecognitionResult = {
  musicxml_url: string | null;
  midi_url: string | null;
  confidence: number;
  engine: string;
  warnings: string[];
  errors: string[];
  extracted_title: string | null;
};

export type MusicAnalysis = {
  key: string;
  time_signature: string;
  tempo: string;
  measure_count: number;
  part_count: number;
  chords: Array<Record<string, unknown>>;
  roman_numerals: Array<Record<string, unknown>>;
  phrases: Array<Record<string, unknown>>;
  texture: string[];
  form_candidates: string[];
  caveats: string[];
};

export type Report = {
  title: string;
  markdown: string;
  html: string;
  pdf_url: string | null;
  generated_at: string;
  provider?: "openai" | "local" | "unknown";
  model?: string | null;
  provider_error?: string | null;
};

export type Project = {
  id: string;
  title: string;
  status: ProjectStatus;
  created_at: string;
  updated_at: string;
  source_filename: string;
  source_url: string;
  source_mime: string;
  recognition: RecognitionResult | null;
  analysis: MusicAnalysis | null;
  report: Report | null;
  error: string | null;
};

export function apiUrl(path: string | null | undefined) {
  if (!path) {
    return "";
  }
  if (path.startsWith("http")) {
    return path;
  }
  return `${API_BASE}${path}`;
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, options);
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail ?? `请求失败：${response.status}`);
  }
  return response.json() as Promise<T>;
}

export async function listProjects() {
  return request<Project[]>("/api/projects");
}

export async function createProject(file: File) {
  const form = new FormData();
  form.append("file", file);
  return request<Project>("/api/projects", {
    method: "POST",
    body: form
  });
}

export async function getProject(id: string) {
  return request<Project>(`/api/projects/${id}`);
}

export async function recognizeProject(id: string) {
  return request<Project>(`/api/projects/${id}/recognize`, { method: "POST" });
}

export async function analyzeProject(id: string) {
  return request<Project>(`/api/projects/${id}/analyze`, { method: "POST" });
}

export async function reportProject(id: string) {
  return request<Project>(`/api/projects/${id}/report`, { method: "POST" });
}
