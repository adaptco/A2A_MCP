const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8010'

export interface KnowledgeSourceStatus {
  key: string
  label: string
  path: string
  exists: boolean
  tags: string[]
  bytes: number
}

export interface AvatarRole {
  agent_name: string
  avatar_id: string
  avatar_name: string
  style: string
  description: string
  system_prompt: string
}

export interface RagHit {
  source_key: string
  source_label: string
  path: string
  chunk_id: string
  score: number
  excerpt: string
}

export interface MusicVideoShot {
  shot_id: string
  index: number
  section: string
  start_second: number
  duration_seconds: number
  focus: string
  lyric_cue?: string | null
  continuity_notes: string[]
  source_hits: RagHit[]
  prompt: string
  sora_payload: Record<string, unknown>
}

export interface ContinuityBible {
  protagonist: string
  vibe: string
  visual_motif: string
  palette: string[]
  camera_language: string[]
  continuity_rules: string[]
  narrative_arc: string[]
  source_anchors: Array<{ label: string; excerpt: string }>
}

export interface SoraBatchArtifact {
  jobs: Array<Record<string, unknown>>
  jsonl: string
  dry_run_command: string
  live_command: string
  stitch_command: string
  output_dir: string
  jobs_file: string
  concat_file: string
  sora_script_path: string
  sora_script_exists: boolean
  openai_api_key_present: boolean
}

export interface AdapterExample {
  example_id: string
  shot_id: string
  system_prompt: string
  user_prompt: string
  assistant_prompt: string
  source_keys: string[]
}

export interface MusicVideoPlanRequest {
  title: string
  concept: string
  lyrics_excerpt?: string
  protagonist: string
  vibe: string
  visual_motif: string
  aspect_ratio: 'landscape' | 'portrait'
  duration_seconds: number
  preferred_clip_seconds?: number
  model: string
  size?: string
  top_k: number
}

export interface MusicVideoPlanResponse {
  title: string
  summary: string
  request: MusicVideoPlanRequest
  planned_duration_seconds: number
  duration_delta_seconds: number
  source_catalog: KnowledgeSourceStatus[]
  avatar_cast: AvatarRole[]
  continuity_bible: ContinuityBible
  shot_plan: MusicVideoShot[]
  sora_batch: SoraBatchArtifact
  adapter_examples: AdapterExample[]
  adapter_dataset_jsonl: string
  lora_attention_map: Record<string, number>
  notes: string[]
}

export interface MusicVideoSourcesResponse {
  source_catalog: KnowledgeSourceStatus[]
  avatar_cast: AvatarRole[]
  sora_script_path: string
  sora_script_exists: boolean
  openai_api_key_present: boolean
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
    ...init,
  })

  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `Request failed with ${response.status}`)
  }

  return response.json() as Promise<T>
}

export function getMusicVideoSources(): Promise<MusicVideoSourcesResponse> {
  return request<MusicVideoSourcesResponse>('/music-video/sources')
}

export function createMusicVideoPlan(
  payload: MusicVideoPlanRequest,
): Promise<MusicVideoPlanResponse> {
  return request<MusicVideoPlanResponse>('/music-video/plan', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}
