"""Context window with sliding history and semantic compression."""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from collections import deque
import json


@dataclass
class Turn:
    """Single conversational turn (agent + user)."""
    turn_id: int
    agent_message: str
    user_feedback: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    is_pinned: bool = False  # Pinned turns never dropped

    def to_dict(self) -> Dict[str, Any]:
        return {
            "turn_id": self.turn_id,
            "agent": self.agent_message,
            "user": self.user_feedback,
            "pinned": self.is_pinned,
            "metadata": self.metadata
        }


class ContextWindow:
    """
    Sliding window context manager with semantic compression.

    Keeps last N turns verbatim; older turns folded into summaries.
    Critical artifacts (spec changes, eval failures) pinned.
    """

    def __init__(self, window_size: int = 15, compression_threshold: int = 20):
        self.window_size = window_size  # Keep N recent turns verbatim
        self.compression_threshold = compression_threshold  # Compress after N total turns
        self._turns: deque = deque(maxlen=window_size)
        self._all_turns: List[Turn] = []  # Full history for compression
        self._compressed_summaries: List[str] = []  # Semantic summaries of old turns
        self._turn_count = 0
        self._pinned_artifacts: List[Dict[str, Any]] = []  # Critical items to preserve

    def add_turn(self, agent_message: str, user_feedback: Optional[str] = None,
                 metadata: Optional[Dict[str, Any]] = None, pinned: bool = False) -> Turn:
        """
        Add a new turn to context.

        Args:
            agent_message: Agent response
            user_feedback: User comment / correction
            metadata: Optional contextual data
            pinned: If True, never compress/drop this turn

        Returns:
            Turn object
        """
        if metadata is None:
            metadata = {}

        turn = Turn(
            turn_id=self._turn_count,
            agent_message=agent_message,
            user_feedback=user_feedback,
            metadata=metadata,
            is_pinned=pinned
        )

        self._turns.append(turn)
        self._all_turns.append(turn)
        self._turn_count += 1

        # Trigger compression if needed
        if len(self._all_turns) >= self.compression_threshold:
            self._compress_old_turns()

        return turn

    def pin_artifact(self, artifact_type: str, content: str, reason: str = "") -> None:
        """
        Pin a critical artifact (spec change, safety policy, eval criterion).
        These are preserved in context indefinitely.
        """
        self._pinned_artifacts.append({
            "type": artifact_type,
            "content": content,
            "reason": reason
        })

    def _compress_old_turns(self) -> None:
        """
        Compress turns older than window_size into semantic summaries.
        Keep pinned turns and recent turns verbatim.
        """
        if len(self._all_turns) <= self.window_size:
            return

        # Identify turns to compress (older, non-pinned)
        cutoff = len(self._all_turns) - self.window_size
        turns_to_compress = [t for t in self._all_turns[:cutoff] if not t.is_pinned]

        if not turns_to_compress:
            return

        # Create summary (in production, call LLM summarizer)
        summary = self._create_summary(turns_to_compress)
        self._compressed_summaries.append(summary)

    def _create_summary(self, turns: List[Turn]) -> str:
        """
        Create semantic summary of old turns.
        Placeholder: join agent messages.
        Production: call sentence-transformer + abstractive summarizer.
        """
        messages = [t.agent_message for t in turns]
        return f"[SUMMARY: {len(messages)} turns] " + " ".join(messages[:50])  # Truncate

    def get_context(self, include_summaries: bool = True) -> str:
        """
        Get full context string for agent prompt.

        Returns:
            Formatted context with recent turns + compressed summaries.
        """
        parts = []

        # Compressed summaries
        if include_summaries and self._compressed_summaries:
            parts.append("=== Historical Context ===")
            parts.extend(self._compressed_summaries[-3:])  # Last 3 summaries
            parts.append("")

        # Pinned artifacts
        if self._pinned_artifacts:
            parts.append("=== Critical Artifacts ===")
            for artifact in self._pinned_artifacts:
                parts.append(f"[{artifact['type']}] {artifact['content'][:100]}")
            parts.append("")

        # Recent turns
        parts.append("=== Recent Turns ===")
        for turn in self._turns:
            parts.append(f"Agent (turn {turn.turn_id}): {turn.agent_message}")
            if turn.user_feedback:
                parts.append(f"User: {turn.user_feedback}")

        return "\n".join(parts)

    def get_json_context(self) -> Dict[str, Any]:
        """Get context as JSON structure."""
        return {
            "turn_count": self._turn_count,
            "window_size": len(self._turns),
            "compressed_summaries": self._compressed_summaries,
            "pinned_artifacts": self._pinned_artifacts,
            "recent_turns": [t.to_dict() for t in self._turns]
        }

    def clear(self) -> None:
        """Clear all context (for new episode)."""
        self._turns.clear()
        self._all_turns.clear()
        self._compressed_summaries.clear()
        self._pinned_artifacts.clear()
        self._turn_count = 0

    def __repr__(self) -> str:
        return f"<ContextWindow turns={len(self._turns)}/{self._turn_count} pinned={len(self._pinned_artifacts)}>"
