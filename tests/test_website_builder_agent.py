from fastapi.testclient import TestClient

from app.main import app
from app.schemas.website_agent import ChatArtifact, WebsiteTemplateRequest
from app.services.website_builder_agent import WebsiteBuilderTemplateAgent


def test_generate_template_uses_artifacts_for_structure():
    agent = WebsiteBuilderTemplateAgent()
    request = WebsiteTemplateRequest(
        app_name="SessionSiteBuilder",
        artifacts=[
            ChatArtifact(
                artifact_id="a-1",
                artifact_type="requirements",
                title="Goal",
                content="Enable teams to ship landing pages from chat templates.",
                tags=["product"],
            ),
            ChatArtifact(
                artifact_id="a-2",
                artifact_type="notes",
                title="Page map",
                content="Page: Home\nPage: Builder\nPage: Templates",
                tags=["page"],
            ),
            ChatArtifact(
                artifact_id="a-3",
                artifact_type="feature",
                title="Feature set",
                content="AI assisted layout generation",
                tags=["ai"],
            ),
            ChatArtifact(
                artifact_id="a-4",
                artifact_type="theme",
                title="Theme",
                content="primary: #111827\naccent: #22D3EE",
            ),
        ],
    )

    template = agent.generate_template(request)

    assert template.app_name == "SessionSiteBuilder"
    assert template.value_proposition.startswith("Enable teams to ship landing pages")
    assert "Home" in template.pages
    assert "Builder" in template.pages
    assert "AI assisted layout generation" in template.features
    assert template.style_tokens["primary"] == "#111827"
    assert "SessionSiteBuilder" in template.starter_prompt


def test_generate_template_falls_back_to_defaults_when_no_artifacts():
    agent = WebsiteBuilderTemplateAgent()
    template = agent.generate_template(WebsiteTemplateRequest(app_name="DefaultSite"))

    assert template.pages
    assert "Drag-and-drop page editor" in template.features
    assert template.style_tokens["primary"] == "#4F46E5"


def test_website_template_route_returns_normalized_payload():
    client = TestClient(app)
    payload = {
        "app_name": "RouteSiteBuilder",
        "artifacts": [
            {
                "artifact_id": "req-1",
                "artifact_type": "requirements",
                "title": "Requirements",
                "content": "Create a no-code website builder for small teams.",
                "tags": ["product"],
            },
            {
                "artifact_id": "theme-1",
                "artifact_type": "theme",
                "title": "Theme",
                "content": "primary: #7C3AED",
                "tags": ["style"],
            },
        ],
    }

    response = client.post("/agent/website-template", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["app_name"] == "RouteSiteBuilder"
    assert body["style_tokens"]["primary"] == "#7C3AED"
    assert "starter_prompt" in body
