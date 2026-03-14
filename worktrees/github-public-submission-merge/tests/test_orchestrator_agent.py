from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from typing import Sequence
import unittest

from app.orchestrator_agent import (
    CoreOrchestratorMergeAgent,
    DirtyWorktreeError,
    MergeCommand,
)


class CoreOrchestratorMergeAgentTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tempdir = tempfile.TemporaryDirectory()
        root = Path(self._tempdir.name)
        self.remote_path = root / "remote.git"
        self._run(["git", "init", "--bare", self.remote_path.as_posix()])

        seed_repo = root / "seed"
        seed_repo.mkdir()
        self._run(["git", "init", "-b", "main"], cwd=seed_repo)
        self._configure_identity(seed_repo)

        (seed_repo / "app.txt").write_text("initial\n", encoding="utf-8")
        self._run(["git", "add", "app.txt"], cwd=seed_repo)
        self._run(["git", "commit", "-m", "Initial commit"], cwd=seed_repo)
        self._run(["git", "remote", "add", "origin", self.remote_path.as_posix()], cwd=seed_repo)
        self._run(["git", "push", "-u", "origin", "main"], cwd=seed_repo)

        # Successful feature branch with an additive change
        self._run(["git", "checkout", "-b", "feature/landing"], cwd=seed_repo)
        (seed_repo / "landing.txt").write_text("landing ready\n", encoding="utf-8")
        self._run(["git", "add", "landing.txt"], cwd=seed_repo)
        self._run(["git", "commit", "-m", "Add landing surface"], cwd=seed_repo)
        self._run(["git", "push", "-u", "origin", "feature/landing"], cwd=seed_repo)

        # Advance main to create divergence
        self._run(["git", "checkout", "main"], cwd=seed_repo)
        (seed_repo / "app.txt").write_text("main update\n", encoding="utf-8")
        self._run(["git", "commit", "-am", "Update main app"], cwd=seed_repo)
        self._run(["git", "push", "origin", "main"], cwd=seed_repo)

        # Conflicting branch branched before the main update
        base_commit = self._run(["git", "rev-parse", "main~1"], cwd=seed_repo).stdout.strip()
        self._run(["git", "checkout", "-b", "feature/conflict", base_commit], cwd=seed_repo)
        (seed_repo / "app.txt").write_text("conflicting update\n", encoding="utf-8")
        self._run(["git", "commit", "-am", "Conflicting change"], cwd=seed_repo)
        self._run(["git", "push", "-u", "origin", "feature/conflict"], cwd=seed_repo)
        self._run(["git", "checkout", "main"], cwd=seed_repo)

        # Fast-forward branch that can be integrated without a merge commit
        self._run(["git", "checkout", "-b", "feature/fastforward"], cwd=seed_repo)
        (seed_repo / "fast.txt").write_text("fast forward ready\n", encoding="utf-8")
        self._run(["git", "add", "fast.txt"], cwd=seed_repo)
        self._run(["git", "commit", "-m", "Add fast-forward payload"], cwd=seed_repo)
        self._run(["git", "push", "-u", "origin", "feature/fastforward"], cwd=seed_repo)
        self._run(["git", "checkout", "main"], cwd=seed_repo)

        # Clone a fresh workspace for the agent under test
        self.clone_path = root / "clone"
        self._run(["git", "clone", self.remote_path.as_posix(), self.clone_path.as_posix()])
        # Some bare repositories default to a detached HEAD; explicitly track main.
        self._run(["git", "checkout", "main"], cwd=self.clone_path)
        self._configure_identity(self.clone_path)

        self.agent = CoreOrchestratorMergeAgent(self.clone_path)

    def tearDown(self) -> None:
        self._tempdir.cleanup()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _run(self, args: Sequence[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(args, cwd=cwd, text=True, capture_output=True, check=True)

    def _configure_identity(self, repo: Path) -> None:
        self._run(["git", "config", "user.name", "Merge Tester"], cwd=repo)
        self._run(["git", "config", "user.email", "merge@example.com"], cwd=repo)

    # ------------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------------
    def test_plan_merges_respects_patterns(self) -> None:
        self.agent.fetch_remote()
        commands = self.agent.plan_merges(include_patterns=("feature/*",))
        branches = {command.branch for command in commands}
        self.assertIn("origin/feature/landing", branches)
        self.assertIn("origin/feature/conflict", branches)
        self.assertIn("origin/feature/fastforward", branches)
        self.assertNotIn("origin/main", branches)
        for command in commands:
            self.assertTrue(command.sha)
            self.assertIsInstance(command.summary, str)

    def test_merge_branch_supports_dry_run_and_real_merge(self) -> None:
        self.agent.fetch_remote()
        dry_run = self.agent.merge_branch("feature/landing", dry_run=True)
        self.assertTrue(dry_run.success)
        self.assertTrue(dry_run.dry_run)
        self.assertFalse((self.clone_path / "landing.txt").exists())

        result = self.agent.merge_branch("origin/feature/landing")
        self.assertTrue(result.success)
        self.assertFalse(result.dry_run)
        self.assertTrue((self.clone_path / "landing.txt").exists())
        self.assertIsNotNone(result.commit)

    def test_merge_all_aborts_on_conflict(self) -> None:
        self.agent.fetch_remote()
        commands = self.agent.plan_merges(
            include_patterns=("feature/*",),
            exclude_patterns=("*fastforward",),
        )
        commands = sorted(commands, key=lambda command: 0 if command.branch.endswith("landing") else 1)

        results = self.agent.merge_all(commands)
        self.assertEqual(len(results), 2)
        self.assertTrue(results[0].success)
        self.assertFalse(results[1].success)
        self.assertIn("conflict", results[1].message.lower())

        status = self._run(["git", "status", "--porcelain"], cwd=self.clone_path).stdout.strip()
        self.assertEqual(status, "")

    def test_merge_requires_clean_worktree(self) -> None:
        self.agent.fetch_remote()
        (self.clone_path / "temp.txt").write_text("dirty\n", encoding="utf-8")
        with self.assertRaises(DirtyWorktreeError):
            self.agent.merge_branch("feature/landing")

    def test_fast_forward_merge_supports_dry_run_and_execution(self) -> None:
        self.agent.fetch_remote()
        head_before = self._run(["git", "rev-parse", "HEAD"], cwd=self.clone_path).stdout.strip()

        dry_run = self.agent.merge_branch("feature/fastforward", dry_run=True, fast_forward=True)
        self.assertTrue(dry_run.success)
        self.assertTrue(dry_run.dry_run)
        head_after = self._run(["git", "rev-parse", "HEAD"], cwd=self.clone_path).stdout.strip()
        self.assertEqual(head_before, head_after)
        self.assertFalse((self.clone_path / "fast.txt").exists())

        result = self.agent.merge_branch("feature/fastforward", fast_forward=True)
        self.assertTrue(result.success)
        self.assertFalse(result.dry_run)
        self.assertTrue((self.clone_path / "fast.txt").exists())
        self.assertIsNotNone(result.commit)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
