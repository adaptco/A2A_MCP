from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
from orchestrator.database_utils import init_db, get_db
from schemas.database import ArtifactModel
from schemas.agent_artifacts import MCPArtifact
from agents.researcher import ResearcherAgent
from agents.coder import CoderAgent
from agents.tester import TesterAgent
import json

app = FastAPI(title="A2A MCP Orchestrator - Phase 2: Self-Healing")

# Initialize agents
researcher = ResearcherAgent()
coder = CoderAgent()
tester = TesterAgent()

# Configuration
MAX_RETRY_ATTEMPTS = 3  # Maximum number of fix attempts

@app.on_event("startup")
def on_startup():
    init_db()
    print("="*60)
    print("🚀 A2A MCP Orchestrator - Phase 2: Self-Healing")
    print("="*60)
    print("Features:")
    print("  ✅ Persistent artifact storage")
    print("  ✅ Full lineage tracking")
    print("  ✅ Automatic bug fixing with feedback loop")
    print("  ✅ Detailed test reports")
    print("="*60)

@app.get("/")
def root():
    return {
        "service": "A2A MCP Orchestrator",
        "version": "2.0",
        "phase": "Self-Healing Feedback Loop",
        "features": [
            "Multi-agent orchestration",
            "Persistent artifacts",
            "Automatic code fixing",
            "Comprehensive testing"
        ]
    }

@app.post("/orchestrate")
async def orchestrate_self_healing_flow(user_query: str, db: Session = Depends(get_db)):
    """
    Enhanced orchestration with self-healing capability.
    
    Flow:
    1. Research → generates requirements
    2. Code → implements solution
    3. Test → validates code
    4. IF test fails → Code fixes issues (up to MAX_RETRY_ATTEMPTS)
    5. IF test passes → return success
    """
    try:
        print("\n" + "="*60)
        print(f"🎯 NEW WORKFLOW: {user_query}")
        print("="*60)
        
        # ============================================================
        # STEP 1: RESEARCH PHASE
        # ============================================================
        print("\n📚 PHASE 1: RESEARCH")
        print("-" * 60)
        
        res_art = await researcher.run(topic=user_query)
        db_res = ArtifactModel(
            id=res_art.artifact_id,
            agent_name=res_art.metadata["agent"],
            version="1.0",
            type=res_art.type,
            content={"text": res_art.content, "metadata": res_art.metadata}
        )
        db.add(db_res)
        db.commit()
        
        print(f"✅ Research complete: {res_art.artifact_id}")
        print(f"   Agent: {res_art.metadata['agent']}")
        
        # ============================================================
        # STEP 2: INITIAL CODE GENERATION
        # ============================================================
        print("\n💻 PHASE 2: CODE GENERATION")
        print("-" * 60)
        
        cod_art = await coder.run(research_artifact=res_art, db=db)
        db_cod = ArtifactModel(
            id=cod_art.artifact_id,
            parent_artifact_id=res_art.artifact_id,
            agent_name=cod_art.metadata["agent"],
            version=cod_art.metadata.get("version", "2.0"),
            type=cod_art.type,
            content={"text": cod_art.content, "metadata": cod_art.metadata}
        )
        db.add(db_cod)
        db.commit()
        
        print(f"✅ Code generated: {cod_art.artifact_id}")
        print(f"   Agent: {cod_art.metadata['agent']}")
        print(f"   Iteration: v{cod_art.metadata.get('iteration', 1)}")
        
        # ============================================================
        # STEP 3: SELF-HEALING TEST & FIX LOOP
        # ============================================================
        print("\n🧪 PHASE 3: TEST & SELF-HEALING LOOP")
        print("-" * 60)
        
        current_code_artifact_id = cod_art.artifact_id
        retry_count = 0
        test_passed = False
        fix_history = []
        
        while retry_count < MAX_RETRY_ATTEMPTS and not test_passed:
            print(f"\n🔍 Test Attempt {retry_count + 1}/{MAX_RETRY_ATTEMPTS}")
            
            # Run tests
            tst_art = await tester.run(code_artifact_id=current_code_artifact_id, db=db)
            
            # Save test report
            db_tst = ArtifactModel(
                id=tst_art.artifact_id,
                parent_artifact_id=current_code_artifact_id,
                agent_name=tst_art.metadata["agent"],
                version=tst_art.metadata.get("version", "2.0"),
                type=tst_art.type,
                content={"text": tst_art.content, "metadata": tst_art.metadata}
            )
            db.add(db_tst)
            db.commit()
            
            test_status = tst_art.metadata.get("result", "UNKNOWN")
            print(f"   Test Status: {test_status}")
            print(f"   Report ID: {tst_art.artifact_id}")
            
            # Check if code needs fixing
            if tst_art.metadata.get("requires_fix", False):
                print(f"\n⚠️  CODE FAILED TESTS - Initiating self-healing...")
                print(f"   Issues found: {tst_art.metadata.get('issues_found', 0)}")
                print(f"   Tests failed: {tst_art.metadata.get('tests_failed', 0)}")
                
                if retry_count < MAX_RETRY_ATTEMPTS - 1:
                    # Generate fix
                    print(f"\n🔧 Sending feedback to Coder for automatic fix...")
                    
                    fixed_cod_art = await coder.fix_code(
                        original_code_artifact_id=current_code_artifact_id,
                        test_report_artifact=tst_art,
                        db=db
                    )
                    
                    # Save fixed code
                    db_fixed_cod = ArtifactModel(
                        id=fixed_cod_art.artifact_id,
                        parent_artifact_id=current_code_artifact_id,
                        agent_name=fixed_cod_art.metadata["agent"],
                        version=fixed_cod_art.metadata.get("version", "2.0"),
                        type=fixed_cod_art.type,
                        content={"text": fixed_cod_art.content, "metadata": fixed_cod_art.metadata}
                    )
                    db.add(db_fixed_cod)
                    db.commit()
                    
                    print(f"✅ Fixed code generated: {fixed_cod_art.artifact_id}")
                    print(f"   Iteration: v{fixed_cod_art.metadata.get('iteration', 2)}")
                    print(f"   Fixes applied: {len(fixed_cod_art.metadata.get('fixed_issues', []))}")
                    
                    # Track fix history
                    fix_history.append({
                        "attempt": retry_count + 1,
                        "original_code_id": current_code_artifact_id,
                        "test_report_id": tst_art.artifact_id,
                        "fixed_code_id": fixed_cod_art.artifact_id,
                        "fixes_applied": fixed_cod_art.metadata.get("fixed_issues", [])
                    })
                    
                    # Update for next iteration
                    current_code_artifact_id = fixed_cod_art.artifact_id
                    retry_count += 1
                else:
                    print(f"\n❌ Maximum retry attempts ({MAX_RETRY_ATTEMPTS}) reached")
                    print(f"   Code still has issues - manual intervention may be required")
                    break
            else:
                # Tests passed!
                print(f"\n✅ ALL TESTS PASSED!")
                if test_status == "PASSED_WITH_WARNINGS":
                    print(f"   Status: PASSED WITH WARNINGS")
                    print(f"   Code is functional but could be improved")
                else:
                    print(f"   Status: FULLY PASSED")
                    print(f"   Code meets all quality standards")
                
                test_passed = True
        
        # ============================================================
        # FINAL SUMMARY
        # ============================================================
        print("\n" + "="*60)
        print("📊 WORKFLOW SUMMARY")
        print("="*60)
        
        # Retrieve final code
        final_code_db = db.query(ArtifactModel).filter(
            ArtifactModel.id == current_code_artifact_id
        ).first()
        
        final_code = final_code_db.content.get("text", "") if final_code_db else ""
        
        # Retrieve final test report
        final_test = db_tst.content.get("text", "")
        
        summary = {
            "status": "SUCCESS" if test_passed else "FAILED_MAX_RETRIES",
            "workflow_id": res_art.artifact_id,
            "phases": {
                "research": {
                    "artifact_id": res_art.artifact_id,
                    "agent": res_art.metadata["agent"]
                },
                "coding": {
                    "initial_artifact_id": cod_art.artifact_id,
                    "final_artifact_id": current_code_artifact_id,
                    "iterations": retry_count + 1
                },
                "testing": {
                    "artifact_id": tst_art.artifact_id,
                    "final_status": test_status,
                    "test_passed": test_passed
                }
            },
            "self_healing": {
                "enabled": True,
                "fix_attempts": retry_count,
                "max_attempts": MAX_RETRY_ATTEMPTS,
                "fixes_history": fix_history
            },
            "final_code": final_code,
            "final_test_report": final_test
        }
        
        print(f"Research ID: {res_art.artifact_id}")
        print(f"Initial Code ID: {cod_art.artifact_id}")
        print(f"Final Code ID: {current_code_artifact_id}")
        print(f"Test Report ID: {tst_art.artifact_id}")
        print(f"Total Fix Attempts: {retry_count}")
        print(f"Final Status: {'✅ PASSED' if test_passed else '❌ FAILED'}")
        print("="*60 + "\n")
        
        return summary
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ ERROR in workflow: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/artifacts/{artifact_id}")
def get_artifact(artifact_id: str, db: Session = Depends(get_db)):
    """Retrieve a specific artifact by ID"""
    artifact = db.query(ArtifactModel).filter(ArtifactModel.id == artifact_id).first()
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    
    return {
        "id": artifact.id,
        "type": artifact.type,
        "agent": artifact.agent_name,
        "version": artifact.version,
        "parent_id": artifact.parent_artifact_id,
        "created_at": artifact.created_at.isoformat(),
        "content": artifact.content
    }

@app.get("/workflow/{root_artifact_id}")
def get_workflow_tree(root_artifact_id: str, db: Session = Depends(get_db)):
    """Get the entire workflow tree starting from a root artifact"""
    def build_tree(artifact_id):
        artifact = db.query(ArtifactModel).filter(ArtifactModel.id == artifact_id).first()
        if not artifact:
            return None
        
        # Find children
        children = db.query(ArtifactModel).filter(
            ArtifactModel.parent_artifact_id == artifact_id
        ).all()
        
        return {
            "id": artifact.id,
            "type": artifact.type,
            "agent": artifact.agent_name,
            "created_at": artifact.created_at.isoformat(),
            "children": [build_tree(child.id) for child in children]
        }
    
    tree = build_tree(root_artifact_id)
    if not tree:
        raise HTTPException(status_code=404, detail="Root artifact not found")
    
    return tree

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
