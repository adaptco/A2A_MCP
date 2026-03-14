"""
Charley Fox Pizza JRPG - Backend API
Role-based enterprise simulator for pizza delivery operations
"""

from fastapi import FastAPI, HTTPException, WebSocket, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import uuid
import logging

# ============================================================================
# DOMAIN MODELS
# ============================================================================

class Phase(str, Enum):
    """Workday phases"""
    OPENING = "opening"
    PREP = "prep"
    ORDERS = "orders"
    BAKING = "baking"
    DELIVERY = "delivery"
    PAYMENT = "payment"

class Role(str, Enum):
    """Player roles"""
    OWNER = "owner"
    MANAGER = "manager"
    COOKS = "cooks"
    FOH = "foh"
    DELIVERY = "delivery"

class QuestStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

# Request/Response Models
class QuestModel(BaseModel):
    id: str
    title: str
    phase: Phase
    reward: int
    effort: int
    role: Role
    description: str
    status: QuestStatus = QuestStatus.PENDING

class GameStateModel(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    party_name: str = "Charley Fox Guild"
    completed_quests: List[str] = []
    gold: int = 0
    heat: int = 28
    progress: int = 0
    notes: str = ""
    current_phase: Phase = Phase.OPENING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class QuestCompletionRequest(BaseModel):
    quest_id: str
    notes: Optional[str] = None

class WorkflowEventModel(BaseModel):
    """Audit trail event"""
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    event_type: str
    role: Role
    phase: Phase
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data: Dict[str, Any]

# ============================================================================
# DOMAIN LOGIC
# ============================================================================

QUESTS = [
    QuestModel(
        id="q1",
        title="Unlock the Oven Keep",
        phase=Phase.OPENING,
        reward=15,
        effort=10,
        role=Role.MANAGER,
        description="Open shift, verify checklist, warm POS, confirm store state."
    ),
    QuestModel(
        id="q2",
        title="Dough Circle Ritual",
        phase=Phase.PREP,
        reward=25,
        effort=20,
        role=Role.COOKS,
        description="Prep dough, cheese, sauce, boxes, and side items before lunch spike."
    ),
    QuestModel(
        id="q3",
        title="Crystal Phone Queue",
        phase=Phase.ORDERS,
        reward=20,
        effort=15,
        role=Role.FOH,
        description="Accept calls, web orders, and counter demand with ETA promises."
    ),
    QuestModel(
        id="q4",
        title="Inferno Throughput",
        phase=Phase.BAKING,
        reward=30,
        effort=25,
        role=Role.COOKS,
        description="Sequence oven loads to prevent bottlenecks while preserving quality."
    ),
    QuestModel(
        id="q5",
        title="Moped of the Red Fox",
        phase=Phase.DELIVERY,
        reward=35,
        effort=25,
        role=Role.DELIVERY,
        description="Bundle route stops, confirm addresses, and complete hot handoff."
    ),
    QuestModel(
        id="q6",
        title="Coins of Closing",
        phase=Phase.PAYMENT,
        reward=18,
        effort=12,
        role=Role.OWNER,
        description="Close register, reconcile card settlements, capture variance and tip flow."
    ),
]

ROLE_META = {
    Role.OWNER: {
        "label": "Owner",
        "mission": "Capital allocation, standards, margin, growth policy, authority map."
    },
    Role.MANAGER: {
        "label": "Manager",
        "mission": "Staffing, shift orchestration, SLA control, escalation, audit trail."
    },
    Role.COOKS: {
        "label": "Cooks",
        "mission": "Prep, oven throughput, quality, waste reduction, station flow."
    },
    Role.FOH: {
        "label": "Front of House",
        "mission": "Order intake, CX, upsell, queue shaping, payment resolution."
    },
    Role.DELIVERY: {
        "label": "Delivery",
        "mission": "Route efficiency, handoff quality, cash/tip integrity, ETA confidence."
    },
}

# ============================================================================
# STATE MANAGER
# ============================================================================

class GameStateManager:
    """In-memory game state (use Redis/PostgreSQL for production)"""
    
    def __init__(self):
        self.sessions: Dict[str, GameStateModel] = {}
        self.events: List[WorkflowEventModel] = []
        self.logger = logging.getLogger(__name__)
    
    def create_session(self, party_name: str = "Charley Fox Guild") -> GameStateModel:
        state = GameStateModel(party_name=party_name)
        self.sessions[state.session_id] = state
        self.logger.info(f"Session created: {state.session_id}")
        return state
    
    def get_session(self, session_id: str) -> GameStateModel:
        if session_id not in self.sessions:
            raise ValueError(f"Session not found: {session_id}")
        return self.sessions[session_id]
    
    def complete_quest(self, session_id: str, quest_id: str, notes: Optional[str] = None) -> GameStateModel:
        state = self.get_session(session_id)
        quest = next((q for q in QUESTS if q.id == quest_id), None)
        
        if not quest:
            raise ValueError(f"Quest not found: {quest_id}")
        
        if quest_id in state.completed_quests:
            raise ValueError(f"Quest already completed: {quest_id}")
        
        # Update state
        state.completed_quests.append(quest_id)
        state.gold += quest.reward
        state.heat = min(100, state.heat + quest.effort)
        state.progress = round((len(state.completed_quests) / len(QUESTS)) * 100)
        state.updated_at = datetime.utcnow()
        
        # Log event
        event = WorkflowEventModel(
            session_id=session_id,
            event_type="quest_completed",
            role=quest.role,
            phase=quest.phase,
            data={
                "quest_id": quest_id,
                "reward": quest.reward,
                "effort": quest.effort,
                "notes": notes or ""
            }
        )
        self.events.append(event)
        self.logger.info(f"Quest completed: {quest_id} | Gold: {state.gold} | Heat: {state.heat}")
        
        return state
    
    def reset_session(self, session_id: str) -> GameStateModel:
        state = self.get_session(session_id)
        state.completed_quests = []
        state.gold = 0
        state.heat = 28
        state.progress = 0
        state.updated_at = datetime.utcnow()
        self.logger.info(f"Session reset: {session_id}")
        return state
    
    def get_audit_trail(self, session_id: str) -> List[WorkflowEventModel]:
        return [e for e in self.events if e.session_id == session_id]

# ============================================================================
# FASTAPI APPLICATION
# ============================================================================

app = FastAPI(
    title="Charley Fox Pizza JRPG API",
    description="Role-based enterprise simulator backend",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global state
state_manager = GameStateManager()

# ============================================================================
# ENDPOINTS
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "version": "1.0.0"}

@app.post("/api/session/create")
async def create_session(party_name: str = "Charley Fox Guild") -> GameStateModel:
    """Create a new game session"""
    return state_manager.create_session(party_name)

@app.get("/api/session/{session_id}")
async def get_session(session_id: str) -> GameStateModel:
    """Get session state"""
    try:
        return state_manager.get_session(session_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.post("/api/session/{session_id}/quest/complete")
async def complete_quest(session_id: str, request: QuestCompletionRequest) -> GameStateModel:
    """Complete a quest"""
    try:
        return state_manager.complete_quest(session_id, request.quest_id, request.notes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/session/{session_id}/reset")
async def reset_session(session_id: str) -> GameStateModel:
    """Reset session state"""
    try:
        return state_manager.reset_session(session_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.get("/api/quests")
async def get_all_quests() -> List[QuestModel]:
    """Get all quests"""
    return QUESTS

@app.get("/api/quests/{phase}")
async def get_quests_by_phase(phase: Phase) -> List[QuestModel]:
    """Get quests by phase"""
    return [q for q in QUESTS if q.phase == phase]

@app.get("/api/roles")
async def get_roles() -> Dict[str, Any]:
    """Get role metadata"""
    return {
        role.value: {
            "label": meta["label"],
            "mission": meta["mission"]
        }
        for role, meta in ROLE_META.items()
    }

@app.get("/api/session/{session_id}/audit-trail")
async def get_audit_trail(session_id: str) -> List[WorkflowEventModel]:
    """Get audit trail for session"""
    try:
        state_manager.get_session(session_id)  # Verify session exists
        return state_manager.get_audit_trail(session_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.post("/api/session/{session_id}/update-notes")
async def update_notes(session_id: str, notes: str) -> GameStateModel:
    """Update session notes"""
    try:
        state = state_manager.get_session(session_id)
        state.notes = notes
        state.updated_at = datetime.utcnow()
        return state
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

# ============================================================================
# WEBSOCKET (Optional: For real-time updates)
# ============================================================================

@app.websocket("/ws/session/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket for real-time game updates"""
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            
            if data["type"] == "complete_quest":
                result = state_manager.complete_quest(
                    session_id,
                    data["quest_id"],
                    data.get("notes")
                )
                await websocket.send_json({
                    "type": "quest_completed",
                    "state": result.dict()
                })
            
            elif data["type"] == "reset":
                result = state_manager.reset_session(session_id)
                await websocket.send_json({
                    "type": "session_reset",
                    "state": result.dict()
                })
            
            elif data["type"] == "get_state":
                result = state_manager.get_session(session_id)
                await websocket.send_json({
                    "type": "state_update",
                    "state": result.dict()
                })
    
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close(code=1011)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
