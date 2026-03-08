from __future__ import annotations

import json
from pathlib import Path

from app.schemas.music_video import MusicVideoPlanRequest
from app.services.music_video_generator import MusicVideoPlanner


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def test_plan_clip_durations_uses_sora_allowed_lengths(tmp_path: Path) -> None:
    planner = MusicVideoPlanner(repo_root=tmp_path, source_overrides={})

    clips = planner.plan_clip_durations(target_seconds=50, preferred_clip_seconds=8)

    assert clips
    assert all(clip in {4, 8, 12} for clip in clips)
    assert abs(sum(clips) - 50) <= 2


def test_sources_response_reports_present_files(tmp_path: Path) -> None:
    planner = MusicVideoPlanner(
        repo_root=tmp_path,
        source_overrides={
            "aria_kernel": _write(tmp_path / "ARIA_KERNEL.md", "# ARIA\nworldline lattice"),
            "wham_agents": _write(tmp_path / "AGENTS.md", "# Agents\nrender worldline"),
            "sovereign_skill": _write(tmp_path / "SKILL.md", "# Skill\nplanner architect coder"),
            "avatar_core": _write(tmp_path / "avatar.py", "class Avatar: pass"),
        },
    )

    response = planner.get_sources_response()

    assert len(response.source_catalog) == 4
    assert all(source.exists for source in response.source_catalog)
    assert response.avatar_cast


def test_plan_builds_shots_batch_and_adapter_examples(tmp_path: Path) -> None:
    planner = MusicVideoPlanner(
        repo_root=tmp_path,
        source_overrides={
            "aria_kernel": _write(
                tmp_path / "ARIA_KERNEL.md",
                "# ARIA\n\nThe system collapses geodesic intent into a worldline plan for an avatar performer.",
            ),
            "wham_agents": _write(
                tmp_path / "AGENTS.md",
                "# WHAM\n\nLattice render agents protect continuity and cinematic geometry.",
            ),
            "sovereign_skill": _write(
                tmp_path / "SKILL.md",
                "# Skill\n\nPlanner, Architect, Coder, Tester, Reviewer route the workflow.",
            ),
            "avatar_core": _write(
                tmp_path / "avatar.py",
                "class AvatarStyle:\n    ENGINEER = 'engineer'\n    DESIGNER = 'designer'\n",
            ),
        },
    )

    plan = planner.plan(
        MusicVideoPlanRequest(
            title="Signal Bloom",
            concept=(
                "A lone avatar performer moves through a lattice city while telemetry "
                "fragments bloom into a larger stage reveal."
            ),
            lyrics_excerpt="signal in the dark, hold the line, break the orbit",
            protagonist="an original synthetic avatar singer",
            vibe="futurist and emotionally restrained",
            visual_motif="worldline lattice and telemetry glass",
            duration_seconds=36,
            preferred_clip_seconds=8,
            aspect_ratio="landscape",
            model="sora-2",
            top_k=3,
        )
    )

    assert plan.shot_plan
    assert plan.planned_duration_seconds in {32, 36, 40}
    assert plan.sora_batch.jobs
    assert plan.adapter_examples
    assert "create-batch" in plan.sora_batch.dry_run_command
    assert "ffmpeg" in plan.sora_batch.stitch_command
    assert any(shot.source_hits for shot in plan.shot_plan)

    jsonl_rows = [json.loads(line) for line in plan.sora_batch.jsonl.splitlines() if line.strip()]
    adapter_rows = [
        json.loads(line) for line in plan.adapter_dataset_jsonl.splitlines() if line.strip()
    ]

    assert len(jsonl_rows) == len(plan.shot_plan)
    assert len(adapter_rows) == len(plan.adapter_examples)
    assert all("prompt" in row for row in jsonl_rows)
    assert plan.continuity_bible.palette
