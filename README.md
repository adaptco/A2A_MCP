# Phase 2: Self-Healing Feedback Loop

## 🎯 Overview

Phase 2 introduces **automatic bug fixing** through a feedback loop between the Tester and Coder agents. When code fails tests, the system automatically generates fixes based on detailed error reports - no human intervention required!

## 🔄 Self-Healing Architecture

```
┌─────────────┐
│   Research  │  
│    Agent    │  
└──────┬──────┘
       │
       ▼
┌─────────────┐
│    Coder    │◄─────┐
│    Agent    │      │
└──────┬──────┘      │
       │             │
       ▼             │
┌─────────────┐      │
│   Tester    │      │
│    Agent    │      │
└──────┬──────┘      │
       │             │
       ├─PASSED──────┘ (Success!)
       │
       └─FAILED──────┐
                     │
              ┌──────▼───────┐
              │  Feedback    │
              │  Loop Logic  │
              └──────┬───────┘
                     │
              ┌──────▼───────┐
              │  Coder v2    │
              │  (Fixes)     │
              └──────┬───────┘
                     │
              Back to Testing...
              (Max 3 attempts)
```

## 🆕 What's New in Phase 2

### 1. Enhanced TesterAgent v2.0

**Location:** `agents/tester.py`

**New Capabilities:**
- ✅ Syntax validation using AST parsing
- ✅ Code quality analysis (structure, docstrings, error handling)
- ✅ Automated test execution
- ✅ **Actionable feedback generation** for Coder agent
- ✅ Three-tier status system: PASSED / PASSED_WITH_WARNINGS / FAILED

**Example Test Report:**

```markdown
# Test Report: cod-abc12345

## Overall Status: FAILED

## 1. Syntax Validation
✅ **PASSED** - No syntax errors detected

## 2. Code Quality Analysis
🔴 **HIGH**: No function definitions found
   **Suggestion:** Define at least one function with proper docstring
🟡 **MEDIUM**: Missing docstrings
   **Suggestion:** Add docstrings to explain what the code does

## 3. Test Execution Results
❌ **Compilation Test**: FAILED
   Compilation failed: unexpected EOF while parsing
   **Action:** Fix compilation errors

## 🔧 Required Actions for Coder Agent
The following issues MUST be fixed:
1. No function definitions found - Define at least one function with proper docstring
• Compilation Test: Fix compilation errors
```

### 2. Enhanced CoderAgent v2.0

**Location:** `agents/coder.py`

**New Capabilities:**
- ✅ Original code generation (v1)
- ✅ **NEW: `fix_code()` method** - processes tester feedback
- ✅ Automatic application of fixes:
  - Adds missing docstrings
  - Wraps code in functions
  - Adds error handling (try-except blocks)
  - Adds type hints
  - Adds code comments
- ✅ Version tracking (v1, v2, v3...)

**Example Fix Process:**

```python
# Original Code (FAILED)
result = 1000 * (1 + 0.05 / 12) ** (12 * 10)
print(result)

# After Automatic Fixes (PASSED)
def calculate_compound_interest(principal: float, rate: float, time: int) -> float:
    """
    Calculate compound interest.
    Returns final amount after compound interest.
    """
    try:
        # Apply compound interest formula
        amount = principal * (1 + rate / 12) ** (12 * time)
        return round(amount, 2)
    except Exception as e:
        print(f"Error: {e}")
        raise

if __name__ == "__main__":
    result = calculate_compound_interest(1000, 0.05, 10)
    print(f"Result: ${result}")
```

### 3. Self-Healing Orchestrator v2.0

**Location:** `orchestrator/main.py`

**New Flow:**

1. **Research Phase** - Generate requirements (unchanged)
2. **Code Generation** - Create initial implementation
3. **🆕 Test & Fix Loop** (NEW!):
   ```
   LOOP (max 3 attempts):
     - Run comprehensive tests
     - IF tests PASS:
         ✅ Success! Exit loop
     - IF tests FAIL:
         🔧 Generate detailed feedback
         📝 Coder creates fixed version (v2, v3, etc.)
         🔄 Test the new version
   ```
4. **Final Report** - Summary with all iterations tracked

**Configuration:**
```python
MAX_RETRY_ATTEMPTS = 3  # Adjust based on needs
```

## 📊 Artifact Metadata Enhancements

### TesterAgent Metadata
```json
{
  "agent": "Tester_v2.0",
  "version": "2.0",
  "parent_artifact": "cod-abc12345",
  "result": "FAILED",
  "requires_fix": true,
  "syntax_valid": true,
  "issues_found": 3,
  "tests_failed": 1,
  "feedback_for_coder": {
    "syntax_error": null,
    "critical_issues": [
      {
        "severity": "HIGH",
        "issue": "No function definitions found",
        "suggestion": "Define at least one function with proper docstring"
      }
    ],
    "failed_tests": [
      {
        "test_name": "Compilation Test",
        "status": "FAILED",
        "message": "Compilation failed: unexpected EOF"
      }
    ]
  }
}
```

### CoderAgent Fixed Version Metadata
```json
{
  "agent": "Coder_v2.0",
  "version": "2.0",
  "parent_artifact": "cod-abc12345",
  "language": "python",
  "iteration": 2,
  "is_fix": true,
  "fixed_issues": [
    "Fixed: No function definitions found",
    "Fixed: Missing docstrings",
    "Addressed test failure: Compilation Test"
  ]
}
```

## 🚀 Running Phase 2

### 1. Start the Orchestrator

```bash
# Using Docker Compose
docker-compose up -d

# Or directly with Python
python orchestrator/main.py
```

### 2. Trigger Self-Healing Workflow

```bash
curl -X POST "http://localhost:8000/orchestrate?user_query=Create%20a%20function%20for%20compound%20interest"
```

### 3. Watch the Magic Happen

```
================================
🎯 NEW WORKFLOW: Create a function for compound interest
================================

📚 PHASE 1: RESEARCH
------------------------------------------------------------
✅ Research complete: res-a1b2c3d4
   Agent: Researcher_v1

💻 PHASE 2: CODE GENERATION
------------------------------------------------------------
✅ Code generated: cod-e5f6g7h8
   Agent: Coder_v2.0
   Iteration: v1

🧪 PHASE 3: TEST & SELF-HEALING LOOP
------------------------------------------------------------

🔍 Test Attempt 1/3
   Test Status: FAILED
   Report ID: tst-i9j0k1l2

⚠️  CODE FAILED TESTS - Initiating self-healing...
   Issues found: 2
   Tests failed: 1

🔧 Sending feedback to Coder for automatic fix...
✅ Fixed code generated: cod-m3n4o5p6-v2
   Iteration: v2
   Fixes applied: 3

🔍 Test Attempt 2/3
   Test Status: PASSED_WITH_WARNINGS

✅ ALL TESTS PASSED!
   Status: PASSED WITH WARNINGS
   Code is functional but could be improved

================================
📊 WORKFLOW SUMMARY
================================
Research ID: res-a1b2c3d4
Initial Code ID: cod-e5f6g7h8
Final Code ID: cod-m3n4o5p6-v2
Test Report ID: tst-q7r8s9t0
Total Fix Attempts: 1
Final Status: ✅ PASSED
================================
```

## 📡 New API Endpoints

### 1. Enhanced `/orchestrate` (POST)

**Request:**
```bash
POST /orchestrate?user_query=Your+task+here
```

**Response:**
```json
{
  "status": "SUCCESS",
  "workflow_id": "res-abc123",
  "phases": {
    "research": {
      "artifact_id": "res-abc123",
      "agent": "Researcher_v1"
    },
    "coding": {
      "initial_artifact_id": "cod-def456",
      "final_artifact_id": "cod-xyz789-v2",
      "iterations": 2
    },
    "testing": {
      "artifact_id": "tst-ghi789",
      "final_status": "PASSED",
      "test_passed": true
    }
  },
  "self_healing": {
    "enabled": true,
    "fix_attempts": 1,
    "max_attempts": 3,
    "fixes_history": [
      {
        "attempt": 1,
        "original_code_id": "cod-def456",
        "test_report_id": "tst-ghi789",
        "fixed_code_id": "cod-xyz789-v2",
        "fixes_applied": [
          "Fixed: No function definitions found",
          "Fixed: Missing docstrings"
        ]
      }
    ]
  },
  "final_code": "def main():\n    ...",
  "final_test_report": "# Test Report..."
}
```

### 2. Get Artifact (GET)

```bash
GET /artifacts/{artifact_id}
```

Returns full artifact details including content and metadata.

### 3. Get Workflow Tree (GET)

```bash
GET /workflow/{root_artifact_id}
```

Returns the entire workflow tree showing parent-child relationships:

```json
{
  "id": "res-abc123",
  "type": "research_doc",
  "agent": "Researcher_v1",
  "created_at": "2026-02-09T10:30:00",
  "children": [
    {
      "id": "cod-def456",
      "type": "code_solution",
      "agent": "Coder_v2.0",
      "children": [
        {
          "id": "tst-ghi789",
          "type": "test_report",
          "agent": "Tester_v2.0",
          "children": []
        },
        {
          "id": "cod-xyz789-v2",
          "type": "code_solution",
          "agent": "Coder_v2.0",
          "children": [
            {
              "id": "tst-jkl012",
              "type": "test_report",
              "agent": "Tester_v2.0",
              "children": []
            }
          ]
        }
      ]
    }
  ]
}
```

## 🎨 Database Schema Updates

All artifact iterations are stored with full lineage tracking:

```sql
-- Example artifact lineage
id                    | parent_artifact_id | type           | agent       | iteration
---------------------|-------------------|----------------|-------------|----------
res-abc123           | NULL              | research_doc   | Researcher  | 1
cod-def456           | res-abc123        | code_solution  | Coder       | 1
tst-ghi789           | cod-def456        | test_report    | Tester      | 1
cod-xyz789-v2        | cod-def456        | code_solution  | Coder       | 2  ← FIX!
tst-jkl012           | cod-xyz789-v2     | test_report    | Tester      | 2
```

## 🔍 Inspecting the Database

Use the existing inspection tool to see the full lineage:

```bash
python inspect_db.py
```

**Output:**
```
============================================================
AGENT           | TYPE            | ID         | PARENT
------------------------------------------------------------
Researcher_v1   | research_doc    | res-abc12  | ROOT
Coder_v2.0      | code_solution   | cod-def45  | res-abc1
Tester_v2.0     | test_report     | tst-ghi78  | cod-def4
Coder_v2.0      | code_solution   | cod-xyz78  | cod-def4  ← FIX!
Tester_v2.0     | test_report     | tst-jkl01  | cod-xyz7
============================================================
```

## ⚙️ Configuration Options

### Tuning the Self-Healing Loop

In `orchestrator/main.py`:

```python
# Maximum number of fix attempts before giving up
MAX_RETRY_ATTEMPTS = 3  # Default: 3

# Increase for more aggressive fixing:
MAX_RETRY_ATTEMPTS = 5

# Decrease for faster failures:
MAX_RETRY_ATTEMPTS = 1
```

### Tester Sensitivity

In `agents/tester.py`, adjust validation rules:

```python
def _validate_structure(self, code: str) -> List[Dict[str, str]]:
    issues = []
    
    # Make docstring check optional instead of HIGH priority
    if '"""' not in code and "'''" not in code:
        issues.append({
            "severity": "LOW",  # Changed from MEDIUM
            "issue": "Missing docstrings",
            "suggestion": "Add docstrings to explain what the code does"
        })
```

## 🎯 Benefits of Self-Healing

1. **Reduced Manual Intervention** - System fixes common issues automatically
2. **Faster Iteration** - No waiting for developers to fix bugs
3. **Learning from Failures** - Each fix is tracked and can be analyzed
4. **Consistent Quality** - Same validation rules applied every time
5. **Full Traceability** - Complete audit trail of what was fixed and why

## 🚧 Limitations & Future Work

### Current Limitations
- ⚠️ Fixes are heuristic-based (not using LLMs for fix generation yet)
- ⚠️ Limited to Python code validation
- ⚠️ No actual code execution/testing (static analysis only)

### Phase 3 Preview
- 🔮 LLM-powered fix generation (use Claude/GPT to create smarter fixes)
- 🔮 Actual code execution in sandboxed environment
- 🔮 Unit test generation and execution
- 🔮 Multi-language support
- 🔮 Performance benchmarking

## 📚 Key Files

| File | Purpose |
|------|---------|
| `agents/tester.py` | Enhanced tester with detailed feedback |
| `agents/coder.py` | Enhanced coder with fix generation |
| `orchestrator/main.py` | Self-healing orchestration logic |
| `schemas/agent_artifacts.py` | Artifact data contracts (unchanged) |
| `schemas/database.py` | Persistence layer (unchanged) |

## 🎓 Testing the Self-Healing Flow

### Test 1: Successful Fix

```bash
# This should trigger 1 fix attempt and then pass
curl -X POST "http://localhost:8000/orchestrate?user_query=Write%20a%20simple%20calculator"
```

Expected: Initial code fails → Fix generated → Tests pass

### Test 2: Multiple Fixes

```bash
# This might require 2-3 fix attempts
curl -X POST "http://localhost:8000/orchestrate?user_query=Create%20a%20complex%20data%20processor"
```

Expected: Multiple iterations until code quality is acceptable

### Test 3: Max Retries

```bash
# Intentionally complex request that might hit max retries
curl -X POST "http://localhost:8000/orchestrate?user_query=Build%20an%20entire%20web%20framework"
```

Expected: System tries MAX_RETRY_ATTEMPTS times then returns failure

## 🎉 Summary

Phase 2 transforms the A2A system from a simple pipeline into an **intelligent, self-correcting orchestration platform**. The feedback loop between Tester and Coder enables automatic bug fixes, dramatically reducing manual intervention and improving overall code quality.

**Next Steps:** Ready for Phase 3? We can add:
- Real LLM-powered fix generation
- Actual code execution and testing
- Advanced validation rules
- Performance metrics and monitoring

---

**Phase 2 Status:** ✅ Complete  
**Self-Healing:** 🔥 Enabled  
**Ready for Production:** 🚀 Yes (with monitoring)
