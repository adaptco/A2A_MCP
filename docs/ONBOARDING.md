# Onboarding Notes

## Optional gated submodule

This repository includes `PhysicalAI-Autonomous-Vehicles` as a submodule that may contain gated upstream content.
It is intentionally configured to be optional in recursive clone workflows.

Initialize it manually only when you have access and explicitly need it:

```bash
git submodule update --init --recursive PhysicalAI-Autonomous-Vehicles
```

## CI/operator guidance

Default CI and day-to-day development should not require the gated submodule.
When running specialized jobs that depend on it, initialize the submodule explicitly in your job/bootstrap step using the command above.
