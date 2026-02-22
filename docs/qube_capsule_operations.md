# QUBE Capsule Workflow Gaps

## Request Summary
The latest instructions ask for staging the `capsule.patentDraft.qube.v1`
package, sealing it, and exporting it through
`capsule.export.qubePatent.v1`. The provided run order expects additional
Make targets (`freeze`, `listener`, `post`, `verify`, `qube-stage`,
`seal`, `qube-export`, optionally `echo-flare`) and the ability to submit
capsule metadata to a council-managed API.

## Repository State
- No `Makefile` is present in the repository, so the requested `make`
  targets cannot be invoked. A project-wide search for `qube-stage`,
  `qube-export`, and related symbols returns no results.
- The OpenAPI definitions, scripts, and tooling currently in the repo do
  not describe the `POST /runs`, `POST /runs/{id}/seal`, or
  `POST /runs/{id}/dao-export` endpoints referenced in the request.
- There are no JSON templates or schema definitions for
  `capsule.patentDraft.qube.v1.json`,
  `capsule.export.qubePatent.v1.request.json`, or
  `capsule.echoFlare.qube.v1.json` within the repo.

Because these assets are absent, the staging and export workflow cannot
be executed or validated inside this environment.

## Information Needed to Proceed
To operationalise the requested workflow, please provide:
1. The `Makefile` (or equivalent scripts) implementing the `freeze`,
   `post`, `verify`, `qube-stage`, `seal`, and `qube-export` targets.
2. The concrete HTTP contract for the orchestrator endpoints
   (e.g. OpenAPI definitions or example `curl` invocations), including
   authentication requirements and sample payloads.
3. Reference JSON documents or schema definitions for the QUBE capsule
   files so that emitted artifacts can be validated.
4. Any required credentials, environment variables, or secrets needed to
   interact with the council APIs from this workspace.

Once those materials are available, the staging and export run order can
be encoded in the repository and exercised locally. Without them the
process remains non-actionable here.
