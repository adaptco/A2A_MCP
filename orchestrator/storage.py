from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from schemas.database import Base, ArtifactModel
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/mcp_db")

class DBManager:
    def __init__(self):
        self.engine = create_engine(DATABASE_URL)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(bind=self.engine)

    def save_artifact(self, artifact):
        db = self.SessionLocal()
        try:
            db_artifact = ArtifactModel(
                id=artifact.artifact_id,
                parent_artifact_id=getattr(artifact, 'parent_artifact_id', None),
                agent_name=getattr(artifact, 'agent_name', 'UnknownAgent'),
                version=getattr(artifact, 'version', '1.0.0'),
                type=artifact.type,
                content=artifact.content
            )
            db.add(db_artifact)
            db.commit()
            return db_artifact
        finally:
            db.close()

    def get_artifact(self, artifact_id):
        db = self.SessionLocal()
        artifact = db.query(ArtifactModel).filter(ArtifactModel.id == artifact_id).first()
        db.close()
        return artifact
```.

### 2. Final Check of `orchestrator/database_utils.py`
Ensure this file is fully populated in VS Code to support the MCP server:
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from schemas.database import Base
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./a2a_mcp.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)
```.

### 3. Execution Command
Once these edits are saved (**Ctrl + S**), run the following command in your VS Code terminal:
```powershell
python test_api.py
```.

### 4. Verification
* **Self-Healing Loop**: You should see the terminal output "🚀 Initiating A2A-MCP Self-Healing Test..." followed by logs from the Coder and Tester agents.
* **Database Persistence**: After the test completes, run `python inspect_db.py` to verify the "A2A-MCP Artifact Trace Log" shows the newly created artifacts.
* **Integration Status**: If you have pushed these changes to GitHub, check the "Agentic Ingestion & LoRA Synthesis" workflow for a green checkmark indicating a successful OIDC handshake and knowledge indexing.
