from __future__ import annotations

import hashlib
import json
import math
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from app.schemas.music_video import (
    AdapterExample,
    AvatarRole,
    ContinuityBible,
    KnowledgeSourceStatus,
    MusicVideoPlanRequest,
    MusicVideoPlanResponse,
    MusicVideoShot,
    MusicVideoSourcesResponse,
    RagHit,
    SoraBatchArtifact,
    SourceAnchor,
)
from world_foundation_model import (
    build_coding_agent_avatar_cast,
    cluster_artifacts,
    deterministic_embedding,
    lora_attention_weights,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SORA_SCRIPT = Path.home() / ".codex" / "skills" / "sora" / "scripts" / "sora.py"
DEFAULT_ARIA_KERNEL = (
    Path.home()
    / ".gemini"
    / "antigravity"
    / "brain"
    / "76015ee3-2626-4ae2-b4db-b969385ca52a"
    / "ARIA_KERNEL.md"
)
DEFAULT_WHAM_AGENTS = Path.home() / ".claude" / "projects" / "docs" / "AGENTS.md"
DEFAULT_SOVEREIGN_SKILL = Path.home() / ".claude" / "projects" / "Skills" / "SKILL.md"
DEFAULT_AVATAR_CORE = REPO_ROOT / "avatars" / "avatar.py"

ALLOWED_SORA_MODELS = {"sora-2", "sora-2-pro"}
ALLOWED_CLIP_SECONDS = (12, 8, 4)

MASTER_BEATS = (
    ("Cold Open", "Introduce the worldline and the protagonist silhouette."),
    ("Verse One", "Establish movement language and the first environmental cue."),
    ("Pre-Chorus", "Compress the frame and build expectation."),
    ("Chorus", "Deliver the signature wide visual payoff."),
    ("Verse Two", "Expand the world and introduce a supporting motif."),
    ("Bridge", "Break the pattern with a sharper contrast move."),
    ("Final Chorus", "Return with a larger scale and stronger continuity."),
    ("Outro", "Resolve on a single iconic image."),
)

CAMERA_PATTERNS = (
    "24mm slow push with a centered horizon",
    "50mm lateral dolly with controlled parallax",
    "85mm orbit with shallow depth and stable subject lock",
    "35mm crane rise that reveals the environment",
    "locked wide shot with motion crossing the frame",
)


@dataclass(frozen=True)
class _SourceSpec:
    key: str
    label: str
    path: Path
    tags: tuple[str, ...]


@dataclass(frozen=True)
class _IndexedChunk:
    source_key: str
    source_label: str
    path: str
    chunk_id: str
    text: str
    embedding: tuple[float, ...]


def _slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return cleaned[:60] or "music-video"


def _quote_windows(path_or_text: str) -> str:
    return '"' + str(path_or_text).replace('"', '\\"') + '"'


def _pydantic_dump(model: object) -> dict:
    if hasattr(model, "model_dump"):
        return model.model_dump()  # type: ignore[return-value]
    if hasattr(model, "dict"):
        return model.dict()  # type: ignore[return-value]
    raise TypeError(f"Unsupported model type: {type(model)!r}")


def _chunk_text(text: str, *, max_chars: int = 800) -> list[str]:
    blocks = [block.strip() for block in re.split(r"\n\s*\n", text) if block.strip()]
    if not blocks:
        return []

    chunks: list[str] = []
    current = ""
    for block in blocks:
        candidate = block if not current else current + "\n\n" + block
        if len(candidate) <= max_chars:
            current = candidate
            continue
        if current:
            chunks.append(current)
        if len(block) <= max_chars:
            current = block
            continue

        for offset in range(0, len(block), max_chars):
            chunks.append(block[offset : offset + max_chars].strip())
        current = ""

    if current:
        chunks.append(current)
    return [chunk for chunk in chunks if chunk]


def _normalize_excerpt(text: str, limit: int = 220) -> str:
    squashed = re.sub(r"\s+", " ", text).strip()
    if len(squashed) <= limit:
        return squashed
    return squashed[: limit - 3].rstrip() + "..."


def _cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    numerator = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return numerator / (left_norm * right_norm)


def _extract_lyric_cues(text: str | None, target_count: int) -> list[str]:
    if not text:
        return []
    raw_parts = [
        part.strip(" -")
        for part in re.split(r"[\n\r]+|[.;,]", text)
        if part.strip(" -")
    ]
    if not raw_parts:
        return []
    if len(raw_parts) >= target_count:
        return raw_parts[:target_count]
    cues: list[str] = []
    for index in range(target_count):
        cues.append(raw_parts[index % len(raw_parts)])
    return cues


def _resolve_palette(vibe: str, visual_motif: str) -> list[str]:
    combined = f"{vibe} {visual_motif}".lower()
    if any(token in combined for token in ("warm", "gold", "amber")):
        return ["burnt amber", "oxide red", "graphite", "cream"]
    if any(token in combined for token in ("dream", "soft", "ethereal")):
        return ["moon silver", "dust rose", "pearl", "slate blue"]
    if any(token in combined for token in ("neon", "futur", "cyber", "lattice")):
        return ["obsidian", "ion blue", "laser cyan", "signal amber"]
    return ["charcoal", "electric teal", "smoke", "soft white"]


def _resolve_size(model: str, aspect_ratio: str, requested_size: str | None) -> str:
    if requested_size:
        return requested_size
    if aspect_ratio == "portrait":
        return "720x1280" if model == "sora-2" else "1024x1792"
    return "1280x720" if model == "sora-2" else "1792x1024"


def _build_story_beats(clip_count: int) -> list[tuple[str, str]]:
    if clip_count <= 1:
        return [MASTER_BEATS[3]]
    if clip_count >= len(MASTER_BEATS):
        beats: list[tuple[str, str]] = []
        for index in range(clip_count):
            label, description = MASTER_BEATS[index % len(MASTER_BEATS)]
            cycle = index // len(MASTER_BEATS) + 1
            beats.append((f"{label} {cycle}" if cycle > 1 else label, description))
        return beats

    positions = []
    span = len(MASTER_BEATS) - 1
    for index in range(clip_count):
        mapped = round(index * span / (clip_count - 1))
        positions.append(mapped)

    beats: list[tuple[str, str]] = []
    used = set()
    for position in positions:
        while position in used and position < span:
            position += 1
        used.add(position)
        beats.append(MASTER_BEATS[min(position, span)])
    return beats


def _build_training_examples(
    shots: Sequence[MusicVideoShot],
    creative_avatar: AvatarRole,
) -> list[AdapterExample]:
    examples: list[AdapterExample] = []
    for shot in shots:
        examples.append(
            AdapterExample(
                example_id=f"adapter-{shot.shot_id}",
                shot_id=shot.shot_id,
                system_prompt=creative_avatar.system_prompt,
                user_prompt=(
                    f"Create {shot.section.lower()} shot {shot.index} for a long-form "
                    f"music video with duration {shot.duration_seconds}s."
                ),
                assistant_prompt=shot.prompt,
                source_keys=sorted({hit.source_key for hit in shot.source_hits}),
            )
        )
    return examples


class MusicVideoPlanner:
    def __init__(
        self,
        *,
        repo_root: Path | None = None,
        source_overrides: dict[str, Path] | None = None,
        sora_script_path: Path | None = None,
    ) -> None:
        self.repo_root = (repo_root or REPO_ROOT).resolve()
        self.source_overrides = source_overrides or {}
        self.sora_script_path = Path(
            os.environ.get("SORA_SCRIPT_PATH", str(sora_script_path or DEFAULT_SORA_SCRIPT))
        )
        self._source_specs = self._build_source_specs()

    def _build_source_specs(self) -> list[_SourceSpec]:
        sources = {
            "aria_kernel": Path(os.environ.get("ARIA_KERNEL_PATH", str(DEFAULT_ARIA_KERNEL))),
            "wham_agents": Path(os.environ.get("WHAM_AGENTS_PATH", str(DEFAULT_WHAM_AGENTS))),
            "sovereign_skill": Path(
                os.environ.get("SOVEREIGN_SKILL_PATH", str(DEFAULT_SOVEREIGN_SKILL))
            ),
            "avatar_core": Path(os.environ.get("AVATAR_CORE_PATH", str(DEFAULT_AVATAR_CORE))),
        }

        for key, override in self.source_overrides.items():
            sources[key] = Path(override)

        return [
            _SourceSpec(
                key="aria_kernel",
                label="ARIA Kernel",
                path=sources["aria_kernel"],
                tags=("kernel", "memory", "agentic-state"),
            ),
            _SourceSpec(
                key="wham_agents",
                label="WHAM Agents Registry",
                path=sources["wham_agents"],
                tags=("agents", "lattice", "rendering"),
            ),
            _SourceSpec(
                key="sovereign_skill",
                label="Sovereign Skill",
                path=sources["sovereign_skill"],
                tags=("orchestration", "workflow", "moe"),
            ),
            _SourceSpec(
                key="avatar_core",
                label="Avatar Core",
                path=sources["avatar_core"],
                tags=("avatar", "personality", "system-prompt"),
            ),
        ]

    def get_source_catalog(self) -> list[KnowledgeSourceStatus]:
        catalog: list[KnowledgeSourceStatus] = []
        for spec in self._source_specs:
            exists = spec.path.exists()
            size = spec.path.stat().st_size if exists else 0
            catalog.append(
                KnowledgeSourceStatus(
                    key=spec.key,
                    label=spec.label,
                    path=str(spec.path),
                    exists=exists,
                    tags=list(spec.tags),
                    bytes=size,
                )
            )
        return catalog

    def get_avatar_cast(self) -> list[AvatarRole]:
        cast_rows = build_coding_agent_avatar_cast()
        avatar_cast: list[AvatarRole] = []
        for row in cast_rows:
            avatar_cast.append(
                AvatarRole(
                    agent_name=row["agent_name"],
                    avatar_id=row["avatar_id"],
                    avatar_name=row["avatar_name"],
                    style=row["style"],
                    description=row["description"],
                    system_prompt=row["system_prompt"],
                )
            )
        return avatar_cast

    def get_sources_response(self) -> MusicVideoSourcesResponse:
        return MusicVideoSourcesResponse(
            source_catalog=self.get_source_catalog(),
            avatar_cast=self.get_avatar_cast(),
            sora_script_path=str(self.sora_script_path),
            sora_script_exists=self.sora_script_path.exists(),
            openai_api_key_present=bool(os.environ.get("OPENAI_API_KEY")),
        )

    def _load_index(self) -> list[_IndexedChunk]:
        indexed_chunks: list[_IndexedChunk] = []
        for spec in self._source_specs:
            if not spec.path.exists():
                continue
            text = spec.path.read_text(encoding="utf-8", errors="ignore")
            for index, chunk in enumerate(_chunk_text(text), start=1):
                indexed_chunks.append(
                    _IndexedChunk(
                        source_key=spec.key,
                        source_label=spec.label,
                        path=str(spec.path),
                        chunk_id=f"{spec.key}:{index}",
                        text=chunk,
                        embedding=tuple(deterministic_embedding(chunk, dimensions=64)),
                    )
                )
        return indexed_chunks

    def query_sources(self, query: str, *, top_k: int = 3) -> list[RagHit]:
        chunks = self._load_index()
        if not chunks:
            return []
        query_embedding = tuple(deterministic_embedding(query, dimensions=64))
        ranked = sorted(
            chunks,
            key=lambda chunk: _cosine_similarity(query_embedding, chunk.embedding),
            reverse=True,
        )
        hits: list[RagHit] = []
        for chunk in ranked[:top_k]:
            hits.append(
                RagHit(
                    source_key=chunk.source_key,
                    source_label=chunk.source_label,
                    path=chunk.path,
                    chunk_id=chunk.chunk_id,
                    score=round(_cosine_similarity(query_embedding, chunk.embedding), 6),
                    excerpt=_normalize_excerpt(chunk.text),
                )
            )
        return hits

    def plan_clip_durations(
        self,
        target_seconds: int,
        preferred_clip_seconds: int | None = None,
    ) -> list[int]:
        allowed = list(ALLOWED_CLIP_SECONDS)
        if preferred_clip_seconds in ALLOWED_CLIP_SECONDS:
            allowed = [preferred_clip_seconds] + [
                value for value in allowed if value != preferred_clip_seconds
            ]

        max_total = max(target_seconds + max(ALLOWED_CLIP_SECONDS), max(ALLOWED_CLIP_SECONDS))
        dp: dict[int, list[int]] = {0: []}
        for total in range(1, max_total + 1):
            best: list[int] | None = None
            for clip_length in allowed:
                previous = dp.get(total - clip_length)
                if previous is None:
                    continue
                candidate = previous + [clip_length]
                if best is None:
                    best = candidate
                    continue
                if len(candidate) < len(best):
                    best = candidate
                    continue
                if len(candidate) == len(best) and sum(candidate) > sum(best):
                    best = candidate
            if best is not None:
                dp[total] = best

        viable = [
            clips
            for total, clips in dp.items()
            if total >= min(ALLOWED_CLIP_SECONDS) and clips
        ]
        viable.sort(
            key=lambda clips: (
                abs(sum(clips) - target_seconds),
                len(clips),
                -sum(clips),
            )
        )
        return viable[0] if viable else [4]

    def plan(self, request: MusicVideoPlanRequest) -> MusicVideoPlanResponse:
        model = request.model.strip().lower()
        if model not in ALLOWED_SORA_MODELS:
            model = "sora-2"

        clip_durations = self.plan_clip_durations(
            request.duration_seconds,
            preferred_clip_seconds=request.preferred_clip_seconds,
        )
        planned_duration = sum(clip_durations)
        output_slug = request.output_slug or _slugify(request.title)
        output_dir = str(self.repo_root / "artifacts" / "music-video-renders" / output_slug)

        source_catalog = self.get_source_catalog()
        avatar_cast = self.get_avatar_cast()
        global_hits = self.query_sources(
            " ".join(
                filter(
                    None,
                    [
                        request.title,
                        request.concept,
                        request.vibe,
                        request.visual_motif,
                        request.lyrics_excerpt or "",
                    ],
                )
            ),
            top_k=max(request.top_k + 1, 4),
        )

        beats = _build_story_beats(len(clip_durations))
        lyric_cues = _extract_lyric_cues(request.lyrics_excerpt, len(clip_durations))
        palette = _resolve_palette(request.vibe, request.visual_motif)
        size = _resolve_size(model, request.aspect_ratio, request.size)

        creative_avatar = next(
            (avatar for avatar in avatar_cast if avatar.style == "designer"),
            avatar_cast[0],
        )
        continuity_avatar = next(
            (
                avatar
                for avatar in avatar_cast
                if avatar.agent_name in {"OrchestrationAgent", "TesterAgent"}
            ),
            avatar_cast[0],
        )

        shot_plan: list[MusicVideoShot] = []
        start_second = 0
        for index, duration_seconds in enumerate(clip_durations, start=1):
            section, focus = beats[index - 1]
            lyric_cue = lyric_cues[index - 1] if index - 1 < len(lyric_cues) else None
            retrieval_query = " ".join(
                filter(
                    None,
                    [
                        request.title,
                        request.concept,
                        section,
                        focus,
                        request.visual_motif,
                        lyric_cue or "",
                    ],
                )
            )
            source_hits = self.query_sources(retrieval_query, top_k=request.top_k)
            source_labels = ", ".join(hit.source_label for hit in source_hits) or "local avatar sources"
            camera = CAMERA_PATTERNS[(index - 1) % len(CAMERA_PATTERNS)]
            continuity_notes = [
                f"Preserve the same protagonist silhouette and wardrobe introduced in shot 1.",
                f"Carry forward the palette anchors: {', '.join(palette)}.",
                "Keep transitions clean so clips can be stitched without hidden cuts.",
                f"Use {source_labels} as style anchors rather than introducing unrelated motifs.",
            ]
            if lyric_cue:
                continuity_notes.append(f"Time motion beats to the lyric cue: {lyric_cue}.")

            prompt_lines = [
                "Use case: long-form music video shot for later stitched assembly",
                f"Primary request: {request.title} - {section}",
                f"Scene/background: {request.concept}",
                f"Subject: {request.protagonist}",
                f"Action: {focus}",
                f"Camera: {camera}",
                f"Lighting/mood: {request.vibe}",
                f"Color palette: {', '.join(palette)}",
                (
                    "Style/format: cinematic futurist performance film, original avatar cast, "
                    f"{request.visual_motif}"
                ),
                f"Timing/beats: {duration_seconds}s clip, shot {index} of {len(clip_durations)}",
                (
                    "Audio: silent performance footage only; align to original music in post, "
                    "do not generate copyrighted music."
                ),
                (
                    "Constraints: keep the same original synthetic performer, preserve continuity "
                    "between clips, no copyrighted characters, no real people, no logos."
                ),
                "Avoid: flicker, identity drift, jitter, abrupt lens changes, extra text overlays",
            ]
            if lyric_cue:
                prompt_lines.insert(
                    9,
                    f'Text (verbatim): "{lyric_cue}"',
                )
            if source_hits:
                prompt_lines.append(
                    "Reference anchors: " + " | ".join(
                        f"{hit.source_label}: {hit.excerpt}" for hit in source_hits
                    )
                )

            prompt = "\n".join(prompt_lines)
            shot_plan.append(
                MusicVideoShot(
                    shot_id=f"shot-{index:02d}",
                    index=index,
                    section=section,
                    start_second=start_second,
                    duration_seconds=duration_seconds,
                    focus=focus,
                    lyric_cue=lyric_cue,
                    continuity_notes=continuity_notes,
                    source_hits=source_hits,
                    prompt=prompt,
                    sora_payload={
                        "model": model,
                        "size": size,
                        "seconds": str(duration_seconds),
                        "prompt": prompt,
                    },
                )
            )
            start_second += duration_seconds

        source_anchors: list[SourceAnchor] = []
        seen_source_labels: set[str] = set()
        for hit in global_hits:
            if hit.source_label in seen_source_labels:
                continue
            seen_source_labels.add(hit.source_label)
            source_anchors.append(SourceAnchor(label=hit.source_label, excerpt=hit.excerpt))

        continuity_bible = ContinuityBible(
            protagonist=request.protagonist,
            vibe=request.vibe,
            visual_motif=request.visual_motif,
            palette=palette,
            camera_language=list(CAMERA_PATTERNS[:3]),
            continuity_rules=[
                "Keep one original synthetic lead performer across every clip.",
                "Maintain the same lens family and color anchors across sections.",
                "Treat every shot as a clean in/out segment for stitch-safe editing.",
                "Use agent documents as continuity references, not as literal on-screen text.",
            ],
            narrative_arc=[shot.section for shot in shot_plan],
            source_anchors=source_anchors[:4],
        )

        batch_jobs = [
            {
                "prompt": shot.prompt,
                "model": model,
                "size": size,
                "seconds": str(shot.duration_seconds),
                "out": f"{shot.shot_id}.json",
            }
            for shot in shot_plan
        ]
        batch_jsonl = "\n".join(json.dumps(job, ensure_ascii=True) for job in batch_jobs)
        jobs_file = str(Path(output_dir) / f"{output_slug}.jobs.jsonl")
        concat_file = str(Path(output_dir) / f"{output_slug}.concat.txt")
        sora_script = str(self.sora_script_path)
        dry_run_command = " ".join(
            [
                "python",
                _quote_windows(sora_script),
                "create-batch",
                "--input",
                _quote_windows(jobs_file),
                "--out-dir",
                _quote_windows(output_dir),
                "--no-augment",
                "--dry-run",
            ]
        )
        live_command = " ".join(
            [
                "python",
                _quote_windows(sora_script),
                "create-batch",
                "--input",
                _quote_windows(jobs_file),
                "--out-dir",
                _quote_windows(output_dir),
                "--no-augment",
            ]
        )
        stitch_command = " ".join(
            [
                "ffmpeg",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                _quote_windows(concat_file),
                "-c",
                "copy",
                _quote_windows(str(Path(output_dir) / f"{output_slug}.full.mp4")),
            ]
        )

        concat_lines = [
            f"file '{(Path(output_dir) / f'{shot.shot_id}.mp4').as_posix()}'" for shot in shot_plan
        ]
        concat_manifest = "\n".join(concat_lines)

        training_artifacts = [
            f"{hit.source_key}:{hit.chunk_id}"
            for shot in shot_plan
            for hit in shot.source_hits
        ] or ["artifact::music-video-default"]
        clustered = cluster_artifacts(training_artifacts, cluster_count=4)
        lora_map = {
            key: round(value, 6)
            for key, value in lora_attention_weights(clustered).items()
        }

        adapter_examples = _build_training_examples(shot_plan, creative_avatar)
        adapter_dataset_jsonl = "\n".join(
            json.dumps(_pydantic_dump(example), ensure_ascii=True)
            for example in adapter_examples
        )

        notes: list[str] = []
        missing_sources = [source.label for source in source_catalog if not source.exists]
        if missing_sources:
            notes.append(
                "Missing source files were skipped: " + ", ".join(sorted(missing_sources))
            )
        if request.lyrics_excerpt:
            notes.append(
                "Lyrics are used only as timing cues. Sync licensed or original music in post."
            )
        if planned_duration != request.duration_seconds:
            notes.append(
                f"Requested {request.duration_seconds}s, planned {planned_duration}s because "
                "Sora clip durations are constrained to 4, 8, or 12 seconds."
            )
        if not os.environ.get("OPENAI_API_KEY"):
            notes.append("OPENAI_API_KEY is not set, so live Sora execution is not ready.")

        summary = (
            f"Built a {len(shot_plan)}-clip Sora plan for '{request.title}' with "
            f"{planned_duration}s of stitched footage, grounded in {len(global_hits)} retrieved "
            "source anchors and exported as batch plus concat artifacts."
        )

        normalized_request = _pydantic_dump(request)
        normalized_request["model"] = model
        normalized_request["size"] = size

        return MusicVideoPlanResponse(
            title=request.title,
            summary=summary,
            request=MusicVideoPlanRequest(**normalized_request),
            planned_duration_seconds=planned_duration,
            duration_delta_seconds=planned_duration - request.duration_seconds,
            source_catalog=source_catalog,
            avatar_cast=avatar_cast,
            continuity_bible=continuity_bible,
            shot_plan=shot_plan,
            sora_batch=SoraBatchArtifact(
                jobs=batch_jobs,
                jsonl=batch_jsonl,
                dry_run_command=dry_run_command,
                live_command=live_command,
                stitch_command=stitch_command,
                output_dir=output_dir,
                jobs_file=jobs_file,
                concat_file=concat_file,
                sora_script_path=sora_script,
                sora_script_exists=self.sora_script_path.exists(),
                openai_api_key_present=bool(os.environ.get("OPENAI_API_KEY")),
            ),
            adapter_examples=adapter_examples,
            adapter_dataset_jsonl=adapter_dataset_jsonl,
            lora_attention_map=lora_map,
            notes=notes,
        )


def build_music_video_plan(request: MusicVideoPlanRequest) -> MusicVideoPlanResponse:
    return MusicVideoPlanner().plan(request)


def get_music_video_sources() -> MusicVideoSourcesResponse:
    return MusicVideoPlanner().get_sources_response()
