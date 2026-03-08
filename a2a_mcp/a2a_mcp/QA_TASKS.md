# QA Task Proposals

## Typo fix – normalize the SSOT acronym
- **Location:** `adaptco-ssot/README.md` lines 2-4.
- **Issue:** The acronym for "Single Source of Truth" is written as `SSoT`, mixing case within the abbreviation.
- **Proposed Task:** Update the heading and introductory sentence to use the conventional all-caps `SSOT` for clarity and consistency.

## Bug fix – skip malformed capsule manifests during discovery
- **Location:** `codex_qernel/capsules.py` lines 50-61.
- **Issue:** `discover_capsule_manifests` only catches `ValueError` from schema validation, so a malformed JSON file raises `json.JSONDecodeError` and aborts catalog refreshes.
- **Proposed Task:** Extend the exception handling to also catch `json.JSONDecodeError` (and optionally log the failure) so a single bad file cannot prevent the runtime from loading the remaining manifests.

## Documentation fix – describe the CODEX_AUTO_REFRESH toggle accurately
- **Location:** `README.md` lines 54-61.
- **Issue:** The configuration table claims `CODEX_AUTO_REFRESH` is "unused but reserved", yet `QernelConfig.from_env` reads the variable to disable the initial auto-refresh.
- **Proposed Task:** Update the README entry to explain that setting `CODEX_AUTO_REFRESH=0` (or `false`/`no`) disables the automatic refresh on startup, matching the implementation.

## Test improvement – cover malformed JSON manifests
- **Location:** `tests/test_codex_qernel.py` lines 13-76.
- **Issue:** The capsule discovery test only exercises manifests missing required keys; it never verifies behavior when a manifest contains invalid JSON, leaving the `json.JSONDecodeError` path untested.
- **Proposed Task:** Add a fixture with malformed JSON (e.g., truncated file) and assert that discovery skips it without raising, ensuring the runtime remains resilient when encountering corrupt files.
