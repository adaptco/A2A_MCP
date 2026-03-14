from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ChatArtifact(BaseModel):
    """A reusable artifact collected from in-session chat output."""

    artifact_id: str
    artifact_type: Literal["requirements", "wireframe", "copy", "theme", "feature", "notes"]
    title: str
    content: str
    tags: list[str] = Field(default_factory=list)


class WebsiteTemplateRequest(BaseModel):
    """Request payload used by the website builder agent."""

    app_name: str = "WebsiteBuilderApp"
    artifacts: list[ChatArtifact] = Field(default_factory=list)


class WebsiteTemplate(BaseModel):
    """Normalized scaffold that can be used to bootstrap a website-building app."""

    app_name: str
    value_proposition: str
    pages: list[str]
    reusable_components: list[str]
    features: list[str]
    style_tokens: dict[str, str]
    starter_prompt: str
