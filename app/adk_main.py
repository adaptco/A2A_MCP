import os

from google.adk.apps.app import App, EventsCompactionConfig
from google.adk.apps.llm_event_summarizer import LlmEventSummarizer
from google.adk.models import Gemini

# Your root_agent should load:
# - kernel.system.txt
# - actions.manifest.yaml
# - schema validators
root_agent = root_agent  # noqa: F821

summarization_llm = Gemini(model="gemini-2.5-flash")
my_summarizer = LlmEventSummarizer(llm=summarization_llm)

app = App(
    name="ai-architecture-specialist",
    root_agent=root_agent,
    events_compaction_config=EventsCompactionConfig(
        compaction_interval=3,
        overlap_size=1,
        summarizer=my_summarizer,
    ),
)


def assert_public_policy() -> None:
    url = os.getenv("PRIVACY_POLICY_URL", "").strip()
    if not url.startswith("https://"):
        raise RuntimeError("FAIL_CLOSED: PRIVACY_POLICY_URL must be a valid https URL.")


if __name__ == "__main__":
    assert_public_policy()
    # app.run()  # depends on your ADK runner/entrypoint conventions
