from __future__ import annotations

import fnmatch
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Mapping, Sequence, Tuple, Union, List


class MergeAgentError(RuntimeError):
    """Base exception for merge orchestration failures."""


class GitCommandError(MergeAgentError):
    """Raised when an underlying git command fails."""

    def __init__(self, cmd: Sequence[str], returncode: int, stdout: str, stderr: str) -> None:
        detail = stderr.strip() or stdout.strip()
        command_display = " ".join(cmd)
        message = f"{command_display} failed with exit code {returncode}"
        if detail:
            message = f"{message}: {detail}"
        super().__init__(message)
        self.cmd = tuple(cmd)
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class DirtyWorktreeError(MergeAgentError):
    """Raised when the repository contains staged or unstaged changes."""

    def __init__(self, status: str) -> None:
        super().__init__("working tree must be clean before running merges")
        self.status = status


@dataclass(frozen=True)
class MergeCommand:
    """Instruction representing a single branch merge."""

    branch: str
    sha: str
    summary: str


@dataclass
class MergeResult:
    """Outcome of attempting to merge a branch into the base."""

    branch: str
    success: bool
    dry_run: bool
    message: str
    commit: str | None = None
    details: Dict[str, str] = field(default_factory=dict)


MergeItem = Union[str, MergeCommand]


class CoreOrchestratorMergeAgent:
    """Agent that fetches, plans, and merges branches headed to the repository."""

    def __init__(
        self,
        repo_path: str | os.PathLike[str],
        *,
        base_branch: str = "main",
        remote: str = "origin",
        env: Mapping[str, str] | None = None,
    ) -> None:
        self._repo_path = Path(repo_path).resolve()
        if not (self._repo_path / ".git").exists():
            raise ValueError(f"{self._repo_path} is not a git repository")

        self.base_branch = base_branch
        self.remote = remote
        self._env = dict(env) if env is not None else None

        self._validate_remote_exists(remote)
        self._validate_branch_exists(base_branch)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    @property
    def repo_path(self) -> Path:
        """Return the absolute repository path managed by the agent."""

        return self._repo_path

    def configure_identity(self, *, name: str, email: str) -> None:
        """Persist the git author identity used for merge commits."""

        self._run_git("config", "user.name", name)
        self._run_git("config", "user.email", email)

    def fetch_remote(self, *, prune: bool = True) -> str:
        """Fetch the latest refs from the configured remote."""

        args = ["fetch"]
        if prune:
            args.append("--prune")
        args.append(self.remote)
        result = self._run_git(*args)
        return (result.stdout + result.stderr).strip()

    def pull_base(self, *, fast_forward_only: bool = True) -> str:
        """Fast-forward the local base branch to match the remote."""

        self.checkout_base()
        args = ["pull"]
        if fast_forward_only:
            args.append("--ff-only")
        args.extend([self.remote, self.base_branch])
        result = self._run_git(*args)
        return (result.stdout + result.stderr).strip()

    def push_base(self) -> str:
        """Push the local base branch to the remote."""

        result = self._run_git("push", self.remote, self.base_branch)
        return (result.stdout + result.stderr).strip()

    def current_branch(self) -> str:
        """Return the currently checked out branch."""

        return self._run_git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()

    def checkout_base(self) -> None:
        """Switch the working tree to the base branch."""

        self._run_git("checkout", self.base_branch)

    def plan_merges(
        self,
        *,
        include_patterns: Sequence[str] | None = None,
        exclude_patterns: Sequence[str] | None = None,
        remote: str | None = None,
    ) -> List[MergeCommand]:
        """Collect remote branches that should be merged.

        Branches are sorted by commit time (newest first). Patterns can match
        either the fully-qualified ref (e.g. ``origin/feature/foo``) or the
        branch suffix without the remote prefix (``feature/foo``).
        """

        remote_name = remote or self.remote
        reference = f"refs/remotes/{remote_name}"
        result = self._run_git(
            "for-each-ref",
            "--sort=-committerdate",
            reference,
            "--format=%(refname:short)|%(objectname)|%(contents:subject)",
        )

        include = tuple(include_patterns or ())
        exclude = tuple(exclude_patterns or ())

        commands: List[MergeCommand] = []
        for line in result.stdout.splitlines():
            if not line:
                continue
            try:
                ref, sha, summary = line.split("|", 2)
            except ValueError:
                continue
            if ref == f"{remote_name}/{self.base_branch}":
                continue

            aliases = self._branch_aliases(ref, remote_name)
            if include and not self._matches_patterns(aliases, include):
                continue
            if exclude and self._matches_patterns(aliases, exclude):
                continue

            commands.append(MergeCommand(branch=ref, sha=sha, summary=summary.strip()))

        return commands

    def merge_branch(
        self,
        branch: str,
        *,
        dry_run: bool = False,
        fast_forward: bool = False,
    ) -> MergeResult:
        """Attempt to merge ``branch`` into the base branch.

        If ``dry_run`` is true the merge is simulated using ``--no-commit`` and
        aborted immediately after checking for conflicts.
        """

        branch_ref = self._normalize_branch(branch)
        self._ensure_clean_worktree()
        self.checkout_base()

        pre_merge_head = self._run_git("rev-parse", "HEAD").stdout.strip()

        args = ["merge"]
        if fast_forward:
            args.append("--ff-only")
        else:
            args.append("--no-ff")
        if dry_run:
            args.append("--no-commit")
        args.append(branch_ref)

        try:
            completed = self._run_git(*args)
        except GitCommandError as exc:
            self._abort_merge(pre_merge_head if dry_run else None)
            message = self._format_failure_message(branch_ref, exc)
            details = {}
            if exc.stdout.strip():
                details["stdout"] = exc.stdout.strip()
            if exc.stderr.strip():
                details["stderr"] = exc.stderr.strip()
            return MergeResult(
                branch=branch_ref,
                success=False,
                dry_run=dry_run,
                message=message,
                details=details,
            )

        if dry_run:
            self._abort_merge(pre_merge_head, fast_forward=fast_forward)
            message = completed.stdout.strip() or completed.stderr.strip()
            if not message:
                message = f"{branch_ref} can merge cleanly into {self.base_branch}"
            return MergeResult(
                branch=branch_ref,
                success=True,
                dry_run=True,
                message=message,
            )

        new_head = self._run_git("rev-parse", "HEAD").stdout.strip()
        message = completed.stdout.strip() or completed.stderr.strip()
        if not message:
            message = f"Merged {branch_ref} into {self.base_branch}"
        return MergeResult(
            branch=branch_ref,
            success=True,
            dry_run=False,
            message=message,
            commit=new_head,
        )

    def merge_all(
        self,
        branches: Sequence[MergeItem],
        *,
        dry_run: bool = False,
        fetch: bool = True,
        sync_base: bool = True,
        fast_forward: bool = False,
    ) -> List[MergeResult]:
        """Merge all provided branches sequentially.

        Processing stops on the first failure and the remaining branches are not
        attempted. The list of ``branches`` may contain raw branch names or
        :class:`MergeCommand` objects produced by :meth:`plan_merges`.
        """

        if not branches:
            return []

        if fetch:
            self.fetch_remote()
        if sync_base:
            self.pull_base()

        results: List[MergeResult] = []
        for item in branches:
            branch_name = item.branch if isinstance(item, MergeCommand) else str(item)
            result = self.merge_branch(branch_name, dry_run=dry_run, fast_forward=fast_forward)

            if isinstance(item, MergeCommand):
                if item.sha:
                    result.details.setdefault("source_sha", item.sha)
                if item.summary:
                    result.details.setdefault("summary", item.summary)

            results.append(result)
            if not result.success:
                break
        return results

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _validate_remote_exists(self, remote: str) -> None:
        remotes = self._run_git("remote").stdout.split()
        if remote not in remotes:
            raise ValueError(f"remote '{remote}' not found in repository")

    def _validate_branch_exists(self, branch: str) -> None:
        if not (self._local_branch_exists(branch) or self._remote_branch_exists(branch)):
            raise ValueError(f"branch '{branch}' not found in repository")

    def _normalize_branch(self, branch: str) -> str:
        cleaned = branch.strip()
        if not cleaned:
            raise ValueError("branch name must be provided")
        if cleaned.startswith("refs/") or cleaned.startswith(f"{self.remote}/"):
            return cleaned

        if self._local_branch_exists(cleaned):
            return cleaned
        if self._remote_branch_exists(cleaned):
            return f"{self.remote}/{cleaned}"
        return f"{self.remote}/{cleaned}"

    def _local_branch_exists(self, branch: str) -> bool:
        if branch.startswith("refs/heads/"):
            ref = branch
        else:
            ref = f"refs/heads/{branch}"
        return self._run_git("show-ref", ref, check=False).returncode == 0

    def _remote_branch_exists(self, branch: str) -> bool:
        if branch.startswith("refs/remotes/"):
            ref = branch
        elif branch.startswith(f"{self.remote}/"):
            ref = f"refs/remotes/{branch}"
        else:
            ref = f"refs/remotes/{self.remote}/{branch}"
        return self._run_git("show-ref", ref, check=False).returncode == 0

    def _ensure_clean_worktree(self) -> None:
        status = self._run_git("status", "--porcelain").stdout
        if status.strip():
            raise DirtyWorktreeError(status)

    def _branch_aliases(self, ref: str, remote: str) -> Tuple[str, ...]:
        if ref.startswith(f"{remote}/"):
            return ref, ref[len(remote) + 1 :]
        return (ref,)

    @staticmethod
    def _matches_patterns(values: Tuple[str, ...], patterns: Sequence[str]) -> bool:
        for pattern in patterns:
            for value in values:
                if fnmatch.fnmatch(value, pattern):
                    return True
        return False

    def _format_failure_message(self, branch: str, exc: GitCommandError) -> str:
        detail = exc.stderr.strip() or exc.stdout.strip()
        if detail:
            return f"Failed to merge {branch}: {detail}"
        return f"Failed to merge {branch}: exit code {exc.returncode}"

    def _abort_merge(
        self,
        pre_merge_head: str | None,
        *,
        fast_forward: bool | None = None,
    ) -> None:
        """Abort the in-progress merge, restoring state on failure."""

        result = self._run_git("merge", "--abort", check=False)
        if result.returncode != 0 and pre_merge_head:
            # ``git merge --abort`` is a no-op for fast-forward merges, so
            # explicitly reset to the recorded head when simulating.
            reset_needed = fast_forward if fast_forward is not None else True
            if reset_needed:
                self._run_git("reset", "--hard", pre_merge_head, check=False)

    def _run_git(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env.setdefault("GIT_TERMINAL_PROMPT", "0")
        if self._env:
            env.update(self._env)

        cmd = ["git", *args]
        result = subprocess.run(
            cmd,
            cwd=self.repo_path,
            env=env,
            text=True,
            capture_output=True,
        )
        if check and result.returncode != 0:
            raise GitCommandError(cmd, result.returncode, result.stdout, result.stderr)
        return result
