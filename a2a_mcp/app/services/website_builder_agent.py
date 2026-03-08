from __future__ import annotations

from collections import Counter

from ..schemas.website_agent import ChatArtifact, WebsiteTemplate, WebsiteTemplateRequest


DEFAULT_PAGES = ["Home", "Templates", "Builder", "Pricing", "Publish"]
DEFAULT_COMPONENTS = ["HeroSection", "TemplateCard", "DragDropCanvas", "StylePanel", "PublishModal"]
DEFAULT_FEATURES = [
    "Drag-and-drop page editor",
    "Template library",
    "Theme customization",
    "Live preview",
    "One-click publish",
]
DEFAULT_STYLE_TOKENS = {
    "primary": "#4F46E5",
    "secondary": "#0EA5E9",
    "accent": "#14B8A6",
    "background": "#0F172A",
    "text": "#E2E8F0",
}


class WebsiteBuilderTemplateAgent:
    """Builds a normalized website-builder scaffold from chat artifacts."""

    def generate_template(self, request: WebsiteTemplateRequest) -> WebsiteTemplate:
        artifacts = request.artifacts
        value_proposition = self._derive_value_proposition(artifacts)
        pages = self._derive_pages(artifacts)
        reusable_components = self._derive_components(artifacts)
        features = self._derive_features(artifacts)
        style_tokens = self._derive_style_tokens(artifacts)
        starter_prompt = self._build_starter_prompt(
            app_name=request.app_name,
            value_proposition=value_proposition,
            pages=pages,
            features=features,
            components=reusable_components,
        )

        return WebsiteTemplate(
            app_name=request.app_name,
            value_proposition=value_proposition,
            pages=pages,
            reusable_components=reusable_components,
            features=features,
            style_tokens=style_tokens,
            starter_prompt=starter_prompt,
        )

    def _derive_value_proposition(self, artifacts: list[ChatArtifact]) -> str:
        for artifact in artifacts:
            if artifact.artifact_type == "requirements":
                return artifact.content.strip().splitlines()[0][:220]
        for artifact in artifacts:
            if artifact.artifact_type == "notes" and artifact.content.strip():
                return artifact.content.strip().splitlines()[0][:220]
        return "Build and publish modern websites quickly with reusable templates and guided editing."

    def _derive_pages(self, artifacts: list[ChatArtifact]) -> list[str]:
        candidates: list[str] = []
        for artifact in artifacts:
            lines = [line.strip("-• \t") for line in artifact.content.splitlines()]
            for line in lines:
                normalized = line.strip()
                if not normalized:
                    continue
                if normalized.lower().startswith("page:"):
                    candidates.append(normalized.split(":", 1)[1].strip().title())
                if "page" in artifact.tags and len(normalized.split()) <= 4:
                    candidates.append(normalized.title())

        merged = [page for page in self._dedupe_title_case(candidates) if page]
        if not merged:
            return DEFAULT_PAGES.copy()

        for default_page in DEFAULT_PAGES:
            if default_page not in merged:
                merged.append(default_page)
            if len(merged) >= 7:
                break
        return merged

    def _derive_components(self, artifacts: list[ChatArtifact]) -> list[str]:
        candidates: list[str] = []
        for artifact in artifacts:
            if artifact.artifact_type not in {"wireframe", "feature", "notes"}:
                continue
            words = artifact.title.replace("-", " ").replace("_", " ").split()
            if words:
                candidates.append("".join(word.capitalize() for word in words) + "Panel")
            for line in artifact.content.splitlines():
                line = line.strip("-• \t")
                if line.lower().startswith("component:"):
                    raw = line.split(":", 1)[1].strip()
                    candidates.append("".join(part.capitalize() for part in raw.split()))

        merged = self._dedupe_title_case(candidates)
        if not merged:
            return DEFAULT_COMPONENTS.copy()

        for default_component in DEFAULT_COMPONENTS:
            if default_component not in merged:
                merged.append(default_component)
            if len(merged) >= 8:
                break
        return merged

    def _derive_features(self, artifacts: list[ChatArtifact]) -> list[str]:
        tagged_features: list[str] = []
        keyword_counter: Counter[str] = Counter()

        for artifact in artifacts:
            if artifact.artifact_type == "feature":
                tagged_features.append(artifact.content.strip())
            content = artifact.content.lower()
            for keyword in ("publish", "ai", "drag", "template", "preview", "analytics", "seo"):
                if keyword in content:
                    keyword_counter[keyword] += 1

        merged: list[str] = [feature for feature in tagged_features if feature]
        if keyword_counter["drag"] and "Drag-and-drop page editor" not in merged:
            merged.append("Drag-and-drop page editor")
        if keyword_counter["template"] and "Template library" not in merged:
            merged.append("Template library")
        if keyword_counter["preview"] and "Live preview" not in merged:
            merged.append("Live preview")
        if keyword_counter["publish"] and "One-click publish" not in merged:
            merged.append("One-click publish")
        if keyword_counter["ai"] and "AI layout and copy assistant" not in merged:
            merged.append("AI layout and copy assistant")
        if keyword_counter["seo"] and "SEO metadata helper" not in merged:
            merged.append("SEO metadata helper")
        if keyword_counter["analytics"] and "Analytics integration" not in merged:
            merged.append("Analytics integration")

        merged = self._dedupe_title_case(merged)
        if not merged:
            return DEFAULT_FEATURES.copy()
        for default_feature in DEFAULT_FEATURES:
            if default_feature not in merged:
                merged.append(default_feature)
            if len(merged) >= 8:
                break
        return merged

    def _derive_style_tokens(self, artifacts: list[ChatArtifact]) -> dict[str, str]:
        tokens = DEFAULT_STYLE_TOKENS.copy()
        for artifact in artifacts:
            if artifact.artifact_type != "theme":
                continue
            for line in artifact.content.splitlines():
                if ":" not in line:
                    continue
                left, right = line.split(":", 1)
                key = left.strip().lower().replace(" ", "_")
                value = right.strip()
                if key and value:
                    tokens[key] = value
        return tokens

    def _build_starter_prompt(
        self,
        *,
        app_name: str,
        value_proposition: str,
        pages: list[str],
        features: list[str],
        components: list[str],
    ) -> str:
        page_list = ", ".join(pages)
        feature_list = ", ".join(features)
        component_list = ", ".join(components)
        return (
            f"Create a production-ready website builder app named {app_name}. "
            f"Core mission: {value_proposition}. "
            f"Required pages: {page_list}. "
            f"Required features: {feature_list}. "
            f"Use reusable components: {component_list}. "
            "Output React + TypeScript architecture with API boundaries and a phased build plan."
        )

    @staticmethod
    def _dedupe_title_case(items: list[str]) -> list[str]:
        seen: set[str] = set()
        output: list[str] = []
        for item in items:
            normalized = item.strip()
            key = normalized.casefold()
            if not normalized or key in seen:
                continue
            seen.add(key)
            output.append(normalized)
        return output
