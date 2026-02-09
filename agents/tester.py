from schemas.agent_artifacts import MCPArtifact
from schemas.database import ArtifactModel
from sqlalchemy.orm import Session
import uuid

class TesterAgent:
    def __init__(self):
        self.name = "Tester_v1.1"

    async def run(self, code_artifact_id: str, db: Session) -> MCPArtifact:
        """
        Retrieves code from DB and produces a persistent test_report.
        """
        # Fetch the coder's work from the database
        db_artifact = db.query(ArtifactModel).filter(ArtifactModel.id == code_artifact_id).first()
        if not db_artifact:
            raise ValueError("Code artifact not found in database.")

        print(f"[{self.name}] Testing code from DB ID: {code_artifact_id}...")
        
        code_content = db_artifact.content.get("text", "")
        test_passed = "def" in code_content # Simple validation logic
        status = "PASSED" if test_passed else "FAILED"
        
        report_content = f"Test Result: {status}\nValidated Code ID: {code_artifact_id}"
        
        return MCPArtifact(
            artifact_id=f"tst-{uuid.uuid4().hex[:8]}",
            type="test_report",
            content=report_content,
            metadata={
                "agent": self.name,
                "parent_artifact": code_artifact_id,
                "result": status
            }
        )
