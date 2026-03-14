"""
Hawkthorne Speedrun Demo with RAG Pipeline

Three-phase dual-purpose design:
  Phase 1: Speedrun trajectory generation
  Phase 2: Backend crawl → RAG embedding
  Phase 3: LoRA-tuned agent/bot execution
"""

import asyncio
import json
import hashlib
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass, field
import numpy as np
from pathlib import Path


# =============================================================================
# PHASE 1: SPEEDRUN TRAJECTORY GENERATION
# =============================================================================

@dataclass
class SpeedrunSegment:
    """A segment of a speedrun with actions and timestamps."""
    name: str
    start_pos: Tuple[float, float]
    end_pos: Tuple[float, float]
    actions: List[Dict[str, Any]]
    duration_frames: int


@dataclass 
class SpeedrunTrajectory:
    """Complete speedrun from start to finish."""
    segments: List[SpeedrunSegment]
    total_frames: int = 0
    worldline_id: str = ""
    
    def __post_init__(self):
        self.total_frames = sum(s.duration_frames for s in self.segments)
        data = json.dumps([s.name for s in self.segments]).encode()
        self.worldline_id = f"sr_{hashlib.sha256(data).hexdigest()[:12]}"


class SpeedrunGenerator:
    """Generates optimal speedrun trajectories for Hawkthorne."""
    
    # Hawkthorne level structure (simplified)
    LEVELS = {
        "town_square": {"spawn": (100, 200), "exits": {"east": "forest"}},
        "forest": {"spawn": (0, 200), "exits": {"east": "castle", "north": "cave"}},
        "cave": {"spawn": (50, 100), "exits": {"south": "forest"}},
        "castle": {"spawn": (0, 200), "exits": {"boss": "throne_room"}},
        "throne_room": {"spawn": (400, 200), "exits": {}},
    }
    
    # Optimal action patterns per segment
    ACTION_PATTERNS = {
        "run_right": [{"action": "move", "dir": "right", "frames": 1}],
        "jump_gap": [{"action": "jump", "frames": 12}, {"action": "move", "dir": "right", "frames": 8}],
        "wall_climb": [{"action": "jump", "frames": 6}, {"action": "wall_jump", "frames": 4}],
        "boss_attack": [{"action": "attack", "frames": 8}, {"action": "dodge", "dir": "left", "frames": 4}],
    }
    
    def generate_any_percent(self) -> SpeedrunTrajectory:
        """Generate any% speedrun (fastest completion)."""
        segments = [
            SpeedrunSegment(
                name="town_to_forest",
                start_pos=self.LEVELS["town_square"]["spawn"],
                end_pos=(800, 200),
                actions=self._repeat_pattern("run_right", 120),
                duration_frames=120
            ),
            SpeedrunSegment(
                name="forest_skip",
                start_pos=self.LEVELS["forest"]["spawn"],
                end_pos=(600, 150),
                actions=self._sequence(["run_right"] * 40 + ["jump_gap"] * 3),
                duration_frames=100
            ),
            SpeedrunSegment(
                name="castle_rush",
                start_pos=self.LEVELS["castle"]["spawn"],
                end_pos=(900, 100),
                actions=self._sequence(["run_right"] * 60 + ["wall_climb"] * 5),
                duration_frames=180
            ),
            SpeedrunSegment(
                name="boss_fight",
                start_pos=self.LEVELS["throne_room"]["spawn"],
                end_pos=(400, 200),
                actions=self._repeat_pattern("boss_attack", 8),
                duration_frames=96
            ),
        ]
        return SpeedrunTrajectory(segments=segments)
    
    def _repeat_pattern(self, pattern: str, count: int) -> List[Dict]:
        return self.ACTION_PATTERNS[pattern] * count
    
    def _sequence(self, patterns: List[str]) -> List[Dict]:
        actions = []
        for p in patterns:
            actions.extend(self.ACTION_PATTERNS.get(p, []))
        return actions


# =============================================================================
# PHASE 2: BACKEND CRAWLER → RAG EMBEDDING
# =============================================================================

@dataclass
class CrawledDocument:
    """A document crawled from the Hawkthorne codebase."""
    path: str
    content: str
    doc_type: str  # "level", "entity", "script", "config"
    embedding: np.ndarray = field(default_factory=lambda: np.array([]))


class HawkthorneCrawler:
    """Crawls Hawkthorne Lua codebase for RAG indexing."""
    
    # Simulated Hawkthorne structure (actual repo: github.com/hawkthorne/hawkthorne-journey)
    MOCK_CODEBASE = {
        "src/levels/town.lua": '''
local Level = require "level"
local Town = Level:new("town")
Town.spawn = {x=100, y=200}
Town.music = "town_theme"
return Town
''',
        "src/levels/forest.lua": '''
local Level = require "level"
local Forest = Level:new("forest") 
Forest.spawn = {x=0, y=200}
Forest.enemies = {"goblin", "spider"}
return Forest
''',
        "src/entities/player.lua": '''
local Player = {}
Player.speed = 200
Player.jump_height = 300
Player.health = 100
function Player:update(dt)
    self.x = self.x + self.vx * dt
end
return Player
''',
        "src/config/game.lua": '''
GAME_VERSION = "0.0.110"
TILE_SIZE = 24
GRAVITY = 1200
MAX_ENEMIES = 20
''',
    }
    
    def crawl(self) -> List[CrawledDocument]:
        """Crawl the codebase and extract documents."""
        docs = []
        for path, content in self.MOCK_CODEBASE.items():
            doc_type = self._classify_doc(path)
            docs.append(CrawledDocument(
                path=path,
                content=content,
                doc_type=doc_type
            ))
        return docs
    
    def _classify_doc(self, path: str) -> str:
        if "levels" in path:
            return "level"
        elif "entities" in path:
            return "entity"
        elif "config" in path:
            return "config"
        return "script"


class RAGEmbedder:
    """Embeds documents into vector space for RAG retrieval."""
    
    def __init__(self, dim: int = 128):
        self.dim = dim
        np.random.seed(42)
        
    def embed(self, doc: CrawledDocument) -> np.ndarray:
        """Generate embedding for document."""
        # Deterministic embedding from content hash
        content_hash = hashlib.sha256(doc.content.encode()).digest()
        seed = int.from_bytes(content_hash[:4], 'big')
        np.random.seed(seed)
        
        vec = np.random.randn(self.dim)
        vec /= np.linalg.norm(vec)
        return vec
    
    def embed_batch(self, docs: List[CrawledDocument]) -> List[CrawledDocument]:
        """Embed batch of documents."""
        for doc in docs:
            doc.embedding = self.embed(doc)
        return docs


class VectorStore:
    """Simple in-memory vector store for RAG."""
    
    def __init__(self):
        self.docs: List[CrawledDocument] = []
        
    def add(self, docs: List[CrawledDocument]):
        self.docs.extend(docs)
        
    def query(self, query_vec: np.ndarray, top_k: int = 3) -> List[Tuple[CrawledDocument, float]]:
        """Find most similar documents."""
        results = []
        for doc in self.docs:
            sim = np.dot(query_vec, doc.embedding)
            results.append((doc, sim))
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]


# =============================================================================
# PHASE 3: LORA-TUNED AGENT/BOT EXECUTION
# =============================================================================

@dataclass
class LoRAConfig:
    """Configuration for LoRA adapter."""
    rank: int = 16
    alpha: float = 32.0
    target_modules: List[str] = field(default_factory=lambda: ["q_proj", "v_proj"])
    
    @property
    def scaling(self) -> float:
        return self.alpha / self.rank


class HawthorneAgent:
    """
    Dual-purpose agent that can:
    1. Play the game autonomously (bot mode)
    2. Generate training data (emulator mode)
    """
    
    def __init__(self, vector_store: VectorStore, lora_config: LoRAConfig = None):
        self.vector_store = vector_store
        self.lora_config = lora_config or LoRAConfig()
        self.mode = "bot"  # "bot" or "emulator"
        self.trajectory_buffer: List[Dict] = []
        
    def set_mode(self, mode: str):
        """Switch between bot and emulator mode."""
        assert mode in ("bot", "emulator")
        self.mode = mode
        
    async def observe(self, game_state: Dict) -> Dict:
        """Observe current game state and retrieve relevant knowledge."""
        # Generate query embedding from state
        state_str = json.dumps(game_state)
        query_vec = self._embed_query(state_str)
        
        # RAG retrieval
        relevant_docs = self.vector_store.query(query_vec, top_k=2)
        
        return {
            "state": game_state,
            "retrieved": [
                {"path": doc.path, "type": doc.doc_type, "score": float(score)}
                for doc, score in relevant_docs
            ]
        }
    
    async def decide(self, observation: Dict) -> Dict:
        """Decide next action based on observation (LoRA-influenced)."""
        state = observation["state"]
        retrieved = observation["retrieved"]
        
        # Use LoRA scaling to weight retrieved knowledge
        knowledge_weight = self.lora_config.scaling
        
        # Simple heuristic decision (would be LLM call in production)
        if state.get("near_enemy", False):
            action = {"type": "attack", "weight": knowledge_weight}
        elif state.get("near_gap", False):
            action = {"type": "jump", "weight": knowledge_weight}
        else:
            action = {"type": "move", "dir": "right", "weight": knowledge_weight}
        
        return action
    
    async def execute(self, action: Dict) -> Dict:
        """Execute action and return result."""
        # In bot mode: send to game
        # In emulator mode: record for training
        result = {
            "action": action,
            "success": True,
            "mode": self.mode
        }
        
        if self.mode == "emulator":
            self.trajectory_buffer.append(action)
        
        return result
    
    def export_trajectory(self) -> List[Dict]:
        """Export recorded trajectory for training."""
        trajectory = self.trajectory_buffer.copy()
        self.trajectory_buffer.clear()
        return trajectory
    
    def _embed_query(self, text: str) -> np.ndarray:
        """Generate query embedding."""
        content_hash = hashlib.sha256(text.encode()).digest()
        seed = int.from_bytes(content_hash[:4], 'big')
        np.random.seed(seed)
        vec = np.random.randn(128)
        return vec / np.linalg.norm(vec)


# =============================================================================
# THREE-PHASE ORCHESTRATOR
# =============================================================================

class ThreePhaseOrchestrator:
    """
    Runs all three phases in one shot:
    1. Generate speedrun trajectory
    2. Crawl backend → RAG embed
    3. Execute agent with LoRA
    """
    
    def __init__(self):
        self.speedrun_gen = SpeedrunGenerator()
        self.crawler = HawkthorneCrawler()
        self.embedder = RAGEmbedder()
        self.vector_store = VectorStore()
        self.agent = None
        
    async def run_all_phases(self) -> Dict[str, Any]:
        """Execute all three phases concurrently where possible."""
        
        results = {"phases": {}}
        
        # PHASE 1: Generate speedrun
        print("=" * 60)
        print("PHASE 1: Generating Speedrun Trajectory")
        print("=" * 60)
        
        speedrun = self.speedrun_gen.generate_any_percent()
        results["phases"]["speedrun"] = {
            "worldline_id": speedrun.worldline_id,
            "total_frames": speedrun.total_frames,
            "segments": [s.name for s in speedrun.segments],
            "estimated_time": f"{speedrun.total_frames / 60:.2f} seconds"
        }
        print(f"  Worldline: {speedrun.worldline_id}")
        print(f"  Segments: {len(speedrun.segments)}")
        print(f"  Total: {speedrun.total_frames} frames")
        
        # PHASE 2: Crawl and embed
        print("\n" + "=" * 60)
        print("PHASE 2: Backend Crawl → RAG Embedding")
        print("=" * 60)
        
        docs = self.crawler.crawl()
        embedded_docs = self.embedder.embed_batch(docs)
        self.vector_store.add(embedded_docs)
        
        results["phases"]["rag"] = {
            "documents_crawled": len(docs),
            "embedding_dim": self.embedder.dim,
            "doc_types": list(set(d.doc_type for d in docs))
        }
        print(f"  Crawled: {len(docs)} documents")
        print(f"  Types: {results['phases']['rag']['doc_types']}")
        
        # PHASE 3: Agent execution
        print("\n" + "=" * 60)
        print("PHASE 3: LoRA Agent Execution")
        print("=" * 60)
        
        self.agent = HawthorneAgent(self.vector_store)
        
        # Simulate game loop for one segment
        game_states = [
            {"x": 100, "y": 200, "level": "town", "near_enemy": False, "near_gap": False},
            {"x": 300, "y": 200, "level": "town", "near_enemy": False, "near_gap": True},
            {"x": 500, "y": 180, "level": "town", "near_enemy": True, "near_gap": False},
        ]
        
        actions_taken = []
        for i, state in enumerate(game_states):
            obs = await self.agent.observe(state)
            action = await self.agent.decide(obs)
            result = await self.agent.execute(action)
            actions_taken.append({
                "frame": i,
                "state": state,
                "action": action["type"],
                "retrieved_docs": len(obs["retrieved"])
            })
        
        results["phases"]["agent"] = {
            "mode": self.agent.mode,
            "lora_rank": self.agent.lora_config.rank,
            "lora_scaling": self.agent.lora_config.scaling,
            "actions_executed": len(actions_taken),
            "action_sequence": [a["action"] for a in actions_taken]
        }
        print(f"  Mode: {self.agent.mode}")
        print(f"  LoRA Rank: {self.agent.lora_config.rank}")
        print(f"  Actions: {results['phases']['agent']['action_sequence']}")
        
        return results


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

async def main():
    """Run complete three-phase demo."""
    print("\n" + "=" * 60)
    print("HAWKTHORNE SPEEDRUN + RAG + LORA DEMO")
    print("Dual-Purpose Design: Agent + Emulator")
    print("=" * 60 + "\n")
    
    orchestrator = ThreePhaseOrchestrator()
    results = await orchestrator.run_all_phases()
    
    print("\n" + "=" * 60)
    print("COMPLETE RESULTS")
    print("=" * 60)
    print(json.dumps(results, indent=2))
    
    return results


if __name__ == "__main__":
    asyncio.run(main())
