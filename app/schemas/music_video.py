from __future__ import annotations

from typing import Any, Dict, List, Literal

from pydantic import BaseModel, Field


class KnowledgeSourceStatus(BaseModel):
    key: str
    label: str
    path: str
    exists: bool
    tags: List[str] = Field(default_factory=list)
    bytes: int = 0


class RagHit(BaseModel):
    source_key: str
    source_label: str
    path: str
    chunk_id: str
    score: float
    excerpt: str


class AvatarRole(BaseModel):
    agent_name: str
    avatar_id: str
    avatar_name: str
    style: str
    description: str
    system_prompt: str


class MusicVideoPlanRequest(BaseModel):
    title: str = Field(min_length=3, max_length=120)
    concept: str = Field(min_length=12, max_length=3000)
    lyrics_excerpt: str | None = Field(default=None, max_length=1200)
    protagonist: str = Field(
        default="an original synthetic avatar performer",
        max_length=200,
    )
    vibe: str = Field(
        default="futurist, cinematic, emotionally precise",
        max_length=240,
    )
    visual_motif: str = Field(
        default="worldline lattice, capsule telemetry, geodesic motion",
        max_length=240,
    )
    aspect_ratio: Literal["landscape", "portrait"] = "landscape"
    duration_seconds: int = Field(default=48, ge=4, le=240)
    preferred_clip_seconds: int | None = Field(default=None, ge=4, le=12)
    model: str = Field(default="sora-2", max_length=40)
    size: str | None = Field(default=None, max_length=32)
    top_k: int = Field(default=3, ge=1, le=6)
    output_slug: str | None = Field(default=None, max_length=120)


class MusicVideoShot(BaseModel):
    shot_id: str
    index: int
    section: str
    start_second: int
    duration_seconds: int
    focus: str
    lyric_cue: str | None = None
    continuity_notes: List[str] = Field(default_factory=list)
    source_hits: List[RagHit] = Field(default_factory=list)
    prompt: str
    sora_payload: Dict[str, Any] = Field(default_factory=dict)


class SourceAnchor(BaseModel):
    label: str
    excerpt: str


class ContinuityBible(BaseModel):
    protagonist: str
    vibe: str
    visual_motif: str
    palette: List[str] = Field(default_factory=list)
    camera_language: List[str] = Field(default_factory=list)
    continuity_rules: List[str] = Field(default_factory=list)
    narrative_arc: List[str] = Field(default_factory=list)
    source_anchors: List[SourceAnchor] = Field(default_factory=list)


class SoraBatchArtifact(BaseModel):
    jobs: List[Dict[str, Any]] = Field(default_factory=list)
    jsonl: str
    dry_run_command: str
    live_command: str
    stitch_command: str
    output_dir: str
    jobs_file: str
    concat_file: str
    sora_script_path: str
    sora_script_exists: bool
    openai_api_key_present: bool


class AdapterExample(BaseModel):
    example_id: str
    shot_id: str
    system_prompt: str
    user_prompt: str
    assistant_prompt: str
    source_keys: List[str] = Field(default_factory=list)


class MusicVideoPlanResponse(BaseModel):
    title: str
    summary: str
    request: MusicVideoPlanRequest
    planned_duration_seconds: int
    duration_delta_seconds: int
    source_catalog: List[KnowledgeSourceStatus] = Field(default_factory=list)
    avatar_cast: List[AvatarRole] = Field(default_factory=list)
    continuity_bible: ContinuityBible
    shot_plan: List[MusicVideoShot] = Field(default_factory=list)
    sora_batch: SoraBatchArtifact
    adapter_examples: List[AdapterExample] = Field(default_factory=list)
    adapter_dataset_jsonl: str
    lora_attention_map: Dict[str, float] = Field(default_factory=dict)
    notes: List[str] = Field(default_factory=list)


class MusicVideoSourcesResponse(BaseModel):
    source_catalog: List[KnowledgeSourceStatus] = Field(default_factory=list)
    avatar_cast: List[AvatarRole] = Field(default_factory=list)
    sora_script_path: str
    sora_script_exists: bool
    openai_api_key_present: bool
