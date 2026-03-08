"""Vector vault for semantic search and pattern matching."""

from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from world_vectors.encoder import EmbeddingEncoder, Embedding


@dataclass
class VaultEntry:
    """Entry in the vector vault."""
    entry_id: str
    embedding: Embedding
    ref_type: str  # "spec", "lore", "agent_bio", "eval_policy", etc.
    retrieval_count: int = 0


class VectorVault:
    """Persistent semantic knowledge vault with cosine similarity search."""

    def __init__(self, encoder: Optional[EmbeddingEncoder] = None):
        self.encoder = encoder or EmbeddingEncoder(dim=768)
        self._entries: Dict[str, VaultEntry] = {}
        self._load_defaults()

    def _load_defaults(self) -> None:
        """Initialize vault with Supra specs from specs/supra_specs.yaml."""
        try:
            from specs.loader import get_loader
            loader = get_loader()

            # Load Supra specs from YAML
            supra_specs = loader.load_supra_specs()

            # Create comprehensive spec entry
            spec_text = f"""
Toyota GR Supra A90 (2024 GT500):
Engine: Twin-Turbo Inline-6, {supra_specs['powertrain']['engine']['hp']} hp, {supra_specs['powertrain']['engine']['torque_lb_ft']} lb-ft torque
Acceleration: 0-60 in {supra_specs['performance']['acceleration']['seconds_0_60']}s
Top Speed: {supra_specs['performance']['vmax_mph']} mph (electronic limiter)
Transmission: {supra_specs['powertrain']['transmission']['type']}
Drivetrain: {supra_specs['powertrain']['drivetrain']}
Weight: {supra_specs['dimensions']['weight_lbs']} lbs
Turning Radius: {supra_specs['handling_characteristics']['steering']['turning_radius_ft']} ft
Braking (60-0): {supra_specs['handling_characteristics']['braking_distance_60_ft']} ft
Fuel Capacity: {supra_specs['performance']['fuel_capacity_gal']} gallons
Handling: {supra_specs['handling_characteristics']['balance']} balance, {supra_specs['handling_characteristics']['skid_pad_g']}g skid pad grip
""".strip()
            self.add_entry("supra_full_spec", spec_text, "spec",
                          metadata={"source": "specs/supra_specs.yaml", "version": "1.0.0"})

            # Add powertrain spec entry
            powertrain_text = f"""
Supra Powertrain: {supra_specs['powertrain']['engine']['type']}
Horsepower: {supra_specs['powertrain']['engine']['hp']}
Torque: {supra_specs['powertrain']['engine']['torque_lb_ft']} lb-ft
Redline: {supra_specs['powertrain']['engine']['redline_rpm']} RPM
Transmission: {supra_specs['powertrain']['transmission']['type']}
Acceleration Profile: 0-60 in {supra_specs['performance']['acceleration']['seconds_0_60']}s, 0-100 in {supra_specs['performance']['acceleration']['seconds_0_100']}s
""".strip()
            self.add_entry("supra_powertrain", powertrain_text, "spec",
                          metadata={"source": "specs/supra_specs.yaml", "category": "powertrain"})

            # Add handling spec entry
            handling_text = f"""
Supra Handling: {supra_specs['handling_characteristics']['balance']} balance RWD platform
Turning Radius: {supra_specs['handling_characteristics']['steering']['turning_radius_ft']} ft
Skid Pad: {supra_specs['handling_characteristics']['skid_pad_g']}g lateral grip
Braking: 60-0 in {supra_specs['handling_characteristics']['braking_distance_60_ft']} ft
Max Lateral G: {supra_specs['performance']['max_acceleration_g']}g
ESC Engagement: {supra_specs['handling_characteristics']['skid_pad_g']}g threshold
""".strip()
            self.add_entry("supra_handling", handling_text, "spec",
                          metadata={"source": "specs/supra_specs.yaml", "category": "handling"})

        except Exception as e:
            # Fallback to hardcoded defaults if specs loading fails
            defaults = [
                ("supra_spec", "Toyota Supra A90: Twin-turbo I6, 335 hp, 0-60 in 3.8s. RWD, 6-speed auto. GT500 trim: carbon fiber, active aero.",
                 "spec"),
                ("base44_lore", "Base44 is a 4-layer logical grid mapping game world. Ground (0-15), Elevated (16-31), Aerial (32-43). System zones 44-47.",
                 "lore"),
            ]
            for ref_id, text, ref_type in defaults:
                self.add_entry(ref_id, text, ref_type)

        # Always add avatar bios
        avatar_bios = [
            ("engineer_bio", "Engineer avatar: precise, safety-conscious, focuses on constraints and failure modes. Blue theme, ⚙️.",
             "agent_bio"),
            ("designer_bio", "Designer avatar: visual, creative, metaphor-rich. Focus on aesthetics and narrative. Purple theme, 🎨.",
             "agent_bio"),
            ("driver_bio", "Driver avatar: game-facing, conversational, engaging. In-universe aware. Red theme, 🏁.",
             "agent_bio"),
            ("safety_policy", "Safety eval policy: ensure no out-of-bounds movement, collision detection, token consumption within cap.",
             "eval_policy"),
        ]
        for ref_id, text, ref_type in avatar_bios:
            self.add_entry(ref_id, text, ref_type)

    def add_entry(self, ref_id: str, text: str, ref_type: str, metadata: Optional[dict] = None) -> VaultEntry:
        """Add a new entry to the vault."""
        if metadata is None:
            metadata = {}
        metadata.update({"ref_type": ref_type, "ref_id": ref_id})
        embedding = self.encoder.encode(text, metadata=metadata)
        entry = VaultEntry(entry_id=ref_id, embedding=embedding, ref_type=ref_type)
        self._entries[ref_id] = entry
        return entry

    def search(self, query: str, top_k: int = 5, ref_type_filter: Optional[str] = None) -> List[Tuple[VaultEntry, float]]:
        """
        Semantic search via cosine similarity.

        Args:
            query: Text query
            top_k: Number of results to return
            ref_type_filter: Optional filter by reference type

        Returns:
            List of (VaultEntry, similarity_score) tuples, sorted by score desc
        """
        query_embedding = self.encoder.encode(query)
        scores = []

        for entry_id, entry in self._entries.items():
            if ref_type_filter and entry.ref_type != ref_type_filter:
                continue

            # Cosine similarity
            sim = self._cosine_similarity(query_embedding.vector, entry.embedding.vector)
            scores.append((entry, sim))

        # Sort by similarity, descending
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]

    def knn_search(self, vector: List[float], top_k: int = 5) -> List[Tuple[VaultEntry, float]]:
        """KNN search using pre-computed vector."""
        scores = []
        for entry_id, entry in self._entries.items():
            sim = self._cosine_similarity(vector, entry.embedding.vector)
            scores.append((entry, sim))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]

    @staticmethod
    def _cosine_similarity(v1: List[float], v2: List[float]) -> float:
        """Compute cosine similarity between two vectors."""
        if len(v1) != len(v2):
            return 0.0
        dot = sum(a * b for a, b in zip(v1, v2))
        norm1 = sum(a ** 2 for a in v1) ** 0.5
        norm2 = sum(b ** 2 for b in v2) ** 0.5
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot / (norm1 * norm2)

    def list_entries(self, ref_type: Optional[str] = None) -> List[VaultEntry]:
        """List all entries, optionally filtered by type."""
        entries = list(self._entries.values())
        if ref_type:
            entries = [e for e in entries if e.ref_type == ref_type]
        return entries

    def __repr__(self) -> str:
        return f"<VectorVault entries={len(self._entries)} encoder={self.encoder}>"
