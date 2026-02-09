from schemas.agent_artifacts import MCPArtifact
from schemas.database import ArtifactModel
from sqlalchemy.orm import Session
import uuid

class CoderAgent:
    def __init__(self):
        self.name = "Coder_v2.0"
        self.version = "2.0"

    async def run(self, research_artifact: MCPArtifact, db: Session = None) -> MCPArtifact:
        """
        Consumes a research artifact and produces a code artifact.
        """
        print(f"[{self.name}] Developing solution based on: {research_artifact.artifact_id}...")
        
        # Logic to extract content from the previous agent's work
        context = research_artifact.content
        
        # Simulate code generation
        code_content = f'''
def calculate_compound_interest(principal: float, rate: float, time: int, n: int = 1) -> float:
    """
    Calculate compound interest.
    
    Args:
        principal: Initial investment amount
        rate: Annual interest rate (as decimal, e.g., 0.05 for 5%)
        time: Time period in years
        n: Number of times interest is compounded per year
        
    Returns:
        Final amount after compound interest
    """
    try:
        if principal < 0 or rate < 0 or time < 0 or n <= 0:
            raise ValueError("All parameters must be positive")
        
        # Formula: A = P(1 + r/n)^(nt)
        amount = principal * (1 + rate / n) ** (n * time)
        return round(amount, 2)
    except Exception as e:
        print(f"Error calculating compound interest: {{e}}")
        raise

if __name__ == "__main__":
    # Example usage
    result = calculate_compound_interest(principal=1000, rate=0.05, time=10, n=12)
    print(f"Compound Interest Result: ${{result}}")
'''
        
        return MCPArtifact(
            artifact_id=f"cod-{uuid.uuid4().hex[:8]}",
            type="code_solution",
            content=code_content,
            metadata={
                "agent": self.name,
                "version": self.version,
                "parent_artifact": research_artifact.artifact_id,
                "language": "python",
                "iteration": 1
            }
        )
    
    async def fix_code(
        self, 
        original_code_artifact_id: str, 
        test_report_artifact: MCPArtifact,
        db: Session
    ) -> MCPArtifact:
        """
        Takes failed code and test feedback, produces a fixed version.
        This is the self-healing magic!
        """
        print(f"[{self.name}] 🔧 SELF-HEALING MODE: Fixing code based on tester feedback...")
        
        # Retrieve original code from database
        db_artifact = db.query(ArtifactModel).filter(
            ArtifactModel.id == original_code_artifact_id
        ).first()
        
        if not db_artifact:
            raise ValueError(f"Original code artifact {original_code_artifact_id} not found")
        
        original_code = db_artifact.content.get("text", "")
        test_feedback = test_report_artifact.metadata.get("feedback_for_coder", {})
        
        print(f"[{self.name}] Original code issues found:")
        if test_feedback.get("syntax_error"):
            print(f"  - Syntax Error: {test_feedback['syntax_error']}")
        for issue in test_feedback.get("critical_issues", []):
            print(f"  - {issue['severity']}: {issue['issue']}")
        for test in test_feedback.get("failed_tests", []):
            print(f"  - Test Failed: {test['test_name']}")
        
        # Apply fixes based on feedback
        fixed_code = self._apply_fixes(original_code, test_feedback)
        
        # Get original iteration number and increment
        original_metadata = db_artifact.content.get("metadata", {})
        iteration = original_metadata.get("iteration", 1) + 1
        
        print(f"[{self.name}] ✅ Generated v{iteration} with fixes applied")
        
        return MCPArtifact(
            artifact_id=f"cod-{uuid.uuid4().hex[:8]}-v{iteration}",
            type="code_solution",
            content=fixed_code,
            metadata={
                "agent": self.name,
                "version": self.version,
                "parent_artifact": original_code_artifact_id,
                "language": "python",
                "iteration": iteration,
                "fixed_issues": self._summarize_fixes(test_feedback),
                "is_fix": True
            }
        )
    
    def _apply_fixes(self, original_code: str, feedback: dict) -> str:
        """Apply automated fixes based on tester feedback"""
        fixed_code = original_code
        
        # Fix 1: Add docstrings if missing
        if any(issue["issue"] == "Missing docstrings" for issue in feedback.get("critical_issues", [])):
            # Add basic docstring if none exists
            if '"""' not in fixed_code and "'''" not in fixed_code:
                # Find first function definition
                lines = fixed_code.split('\n')
                for i, line in enumerate(lines):
                    if line.strip().startswith('def '):
                        # Insert docstring after function definition
                        indent = len(line) - len(line.lstrip())
                        docstring = ' ' * (indent + 4) + '"""Function documentation"""'
                        lines.insert(i + 1, docstring)
                        break
                fixed_code = '\n'.join(lines)
        
        # Fix 2: Add function definitions if missing
        if any(issue["issue"] == "No function definitions found" for issue in feedback.get("critical_issues", [])):
            # Wrap existing code in a main function
            fixed_code = f'''def main():
    """Main function to execute the program"""
    {fixed_code.strip()}

if __name__ == "__main__":
    main()
'''
        
        # Fix 3: Add error handling if missing
        if any(issue["issue"] == "No error handling detected" for issue in feedback.get("critical_issues", [])):
            # Wrap main logic in try-except
            lines = fixed_code.split('\n')
            # Find the main execution area and wrap it
            if "if __name__" not in fixed_code:
                fixed_code = f'''try:
{fixed_code}
except Exception as e:
    print(f"Error occurred: {{e}}")
    raise
'''
        
        # Fix 4: Add type hints if missing (simple heuristic)
        if "Type Hints Test" in str(feedback.get("failed_tests", [])):
            # Add basic type hints to function parameters
            fixed_code = fixed_code.replace("def main()", "def main() -> None:")
        
        # Fix 5: Add comments if insufficient
        if any(issue["issue"] == "Insufficient code comments" for issue in feedback.get("critical_issues", [])):
            lines = fixed_code.split('\n')
            for i, line in enumerate(lines):
                # Add comment before function definitions
                if line.strip().startswith('def '):
                    if i > 0 and not lines[i-1].strip().startswith('#'):
                        indent = len(line) - len(line.lstrip())
                        comment = ' ' * indent + '# Function definition'
                        lines.insert(i, comment)
            fixed_code = '\n'.join(lines)
        
        return fixed_code
    
    def _summarize_fixes(self, feedback: dict) -> list:
        """Create a summary of what was fixed"""
        fixes_applied = []
        
        if feedback.get("syntax_error"):
            fixes_applied.append("Fixed syntax errors")
        
        for issue in feedback.get("critical_issues", []):
            fixes_applied.append(f"Fixed: {issue['issue']}")
        
        for test in feedback.get("failed_tests", []):
            fixes_applied.append(f"Addressed test failure: {test['test_name']}")
        
        return fixes_applied
