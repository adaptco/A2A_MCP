from orchestrator.policy_composer import PolicyComposer
from schemas.prompt_inputs import PromptIntent


def test_policy_composer_uses_deterministic_constraint_order():
    intent = PromptIntent(
        user_input="Ship feature X",
        task_context="Sprint context",
        system_constraints=["System A"],
        workflow_constraints=["Workflow B"],
    )

    system_prompt = PolicyComposer.compose_system_prompt(intent)
    lines = system_prompt.splitlines()

    assert lines[0] == "System constraints (ordered):"
    assert lines[1].endswith("You are a helpful coding assistant.")
    assert lines[2].endswith("Follow repository contracts and return clear, actionable outputs.")
    assert lines[3].endswith("System A")
    assert lines[4].endswith("Workflow B")


def test_policy_composer_places_user_payload_after_constraints():
    intent = PromptIntent(
        task_context="Context goes here",
        user_input="Do the task",
    )

    user_payload = PolicyComposer.compose_user_payload(intent)

    assert user_payload.startswith("Task context:\nContext goes here")
    assert user_payload.endswith("User input:\nDo the task")
