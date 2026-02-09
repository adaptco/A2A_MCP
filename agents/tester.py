from schemas.agent_artifacts import MCPArtifact
from schemas.database import ArtifactModel
from sqlalchemy.orm import Session
import uuid
import ast
import traceback
from typing import List, Dict

class TesterAgent:
    def __init__(self):
        self.name = "Tester_v2.0"
        self.version = "2.0"

    def _validate_syntax(self, code: str) -> Dict[str, any]:
        """Check for Python syntax errors"""
        try:
            ast.parse(code)
            return {"passed": True, "issue": None}
        except SyntaxError as e:
            return {
                "passed": False,
                "issue": f"Syntax Error at line {e.lineno}: {e.msg}",
                "suggestion": "Fix the syntax error before proceeding"
            }

    def _validate_structure(self, code: str) -> List[Dict[str, str]]:
        """Check for code quality issues"""
        issues = []
        
        # Check for function definitions
        if "def " not in code:
            issues.append({
                "severity": "HIGH",
                "issue": "No function definitions found",
                "suggestion": "Define at least one function with proper docstring"
            })
        
        # Check for docstrings
        if '"""' not in code and "'''" not in code:
            issues.append({
                "severity": "MEDIUM",
                "issue": "Missing docstrings",
                "suggestion": "Add docstrings to explain what the code does"
            })
        
        # Check for error handling
        if "try:" not in code and "except" not in code:
            issues.append({
                "severity": "MEDIUM",
                "issue": "No error handling detected",
                "suggestion": "Add try-except blocks for robust error handling"
            })
        
        # Check for comments
        if "#" not in code or code.count("#") < 2:
            issues.append({
                "severity": "LOW",
                "issue": "Insufficient code comments",
                "suggestion": "Add more inline comments to explain logic"
            })
        
        return issues

    def _run_basic_tests(self, code: str) -> List[Dict[str, str]]:
        """Simulate running basic tests on the code"""
        test_results = []
        
        # Test 1: Check if code is executable
        try:
            compile(code, '<string>', 'exec')
            test_results.append({
                "test_name": "Compilation Test",
                "status": "PASSED",
                "message": "Code compiles successfully"
            })
        except Exception as e:
            test_results.append({
                "test_name": "Compilation Test",
                "status": "FAILED",
                "message": f"Compilation failed: {str(e)}",
                "suggestion": "Fix compilation errors"
            })
        
        # Test 2: Check for main execution block
        if '__name__' in code and '__main__' in code:
            test_results.append({
                "test_name": "Main Block Test",
                "status": "PASSED",
                "message": "Has proper main execution block"
            })
        else:
            test_results.append({
                "test_name": "Main Block Test",
                "status": "WARNING",
                "message": "No main execution block found",
                "suggestion": "Add 'if __name__ == \"__main__\":' block for testing"
            })
        
        # Test 3: Check for type hints
        if '->' in code or ': str' in code or ': int' in code:
            test_results.append({
                "test_name": "Type Hints Test",
                "status": "PASSED",
                "message": "Type hints detected"
            })
        else:
            test_results.append({
                "test_name": "Type Hints Test",
                "status": "WARNING",
                "message": "No type hints found",
                "suggestion": "Add type hints for better code clarity"
            })
        
        return test_results

    async def run(self, code_artifact_id: str, db: Session) -> MCPArtifact:
        """
        Retrieves code from DB and produces detailed test report with actionable feedback.
        """
        # Fetch the coder's work from the database
        db_artifact = db.query(ArtifactModel).filter(ArtifactModel.id == code_artifact_id).first()
        if not db_artifact:
            raise ValueError("Code artifact not found in database.")

        print(f"[{self.name}] Running comprehensive tests on code from DB ID: {code_artifact_id}...")
        
        code_content = db_artifact.content.get("text", "")
        
        # Run all validations
        syntax_result = self._validate_syntax(code_content)
        structure_issues = self._validate_structure(code_content)
        test_results = self._run_basic_tests(code_content)
        
        # Determine overall status
        has_syntax_error = not syntax_result["passed"]
        has_high_severity = any(issue["severity"] == "HIGH" for issue in structure_issues)
        has_failed_tests = any(result["status"] == "FAILED" for result in test_results)
        
        if has_syntax_error or has_high_severity or has_failed_tests:
            overall_status = "FAILED"
        elif structure_issues or any(result["status"] == "WARNING" for result in test_results):
            overall_status = "PASSED_WITH_WARNINGS"
        else:
            overall_status = "PASSED"
        
        # Build detailed report
        report_sections = []
        
        report_sections.append(f"# Test Report: {code_artifact_id}")
        report_sections.append(f"\n## Overall Status: {overall_status}\n")
        
        # Syntax validation section
        report_sections.append("## 1. Syntax Validation")
        if syntax_result["passed"]:
            report_sections.append("✅ **PASSED** - No syntax errors detected\n")
        else:
            report_sections.append(f"❌ **FAILED** - {syntax_result['issue']}")
            report_sections.append(f"**Fix Required:** {syntax_result['suggestion']}\n")
        
        # Structure validation section
        report_sections.append("## 2. Code Quality Analysis")
        if not structure_issues:
            report_sections.append("✅ **PASSED** - Code structure looks good\n")
        else:
            for issue in structure_issues:
                severity_emoji = "🔴" if issue["severity"] == "HIGH" else "🟡" if issue["severity"] == "MEDIUM" else "🔵"
                report_sections.append(f"{severity_emoji} **{issue['severity']}**: {issue['issue']}")
                report_sections.append(f"   **Suggestion:** {issue['suggestion']}")
            report_sections.append("")
        
        # Test results section
        report_sections.append("## 3. Test Execution Results")
        for result in test_results:
            status_emoji = "✅" if result["status"] == "PASSED" else "⚠️" if result["status"] == "WARNING" else "❌"
            report_sections.append(f"{status_emoji} **{result['test_name']}**: {result['status']}")
            report_sections.append(f"   {result['message']}")
            if "suggestion" in result:
                report_sections.append(f"   **Action:** {result['suggestion']}")
        report_sections.append("")
        
        # Actionable recommendations section
        if overall_status == "FAILED":
            report_sections.append("## 🔧 Required Actions for Coder Agent")
            report_sections.append("The following issues MUST be fixed:")
            
            if has_syntax_error:
                report_sections.append(f"1. Fix syntax error: {syntax_result['issue']}")
            
            for idx, issue in enumerate([i for i in structure_issues if i["severity"] == "HIGH"], start=2):
                report_sections.append(f"{idx}. {issue['issue']} - {issue['suggestion']}")
            
            for result in [r for r in test_results if r["status"] == "FAILED"]:
                report_sections.append(f"• {result['test_name']}: {result.get('suggestion', 'Review and fix')}")
        
        report_content = "\n".join(report_sections)
        
        # Prepare metadata with structured feedback
        metadata = {
            "agent": self.name,
            "version": self.version,
            "parent_artifact": code_artifact_id,
            "result": overall_status,
            "requires_fix": overall_status == "FAILED",
            "syntax_valid": syntax_result["passed"],
            "issues_found": len(structure_issues),
            "tests_failed": sum(1 for r in test_results if r["status"] == "FAILED")
        }
        
        # Add specific issues for coder to address
        if overall_status == "FAILED":
            metadata["feedback_for_coder"] = {
                "syntax_error": None if syntax_result["passed"] else syntax_result["issue"],
                "critical_issues": [i for i in structure_issues if i["severity"] == "HIGH"],
                "failed_tests": [r for r in test_results if r["status"] == "FAILED"]
            }
        
        print(f"[{self.name}] Test completed with status: {overall_status}")
        if overall_status == "FAILED":
            print(f"[{self.name}] ⚠️  Code requires fixes - returning detailed feedback")
        
        return MCPArtifact(
            artifact_id=f"tst-{uuid.uuid4().hex[:8]}",
            type="test_report",
            content=report_content,
            metadata=metadata
        )
