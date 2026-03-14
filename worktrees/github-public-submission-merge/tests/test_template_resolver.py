from __future__ import annotations

import pytest

from core_orchestrator.template_resolver import PRTemplateResolver, UnknownPRTemplateError


def test_template_resolver_resolves_known_template_id():
    resolver = PRTemplateResolver()

    template = resolver.resolve("PRT.AUTO_REPAIR.V1")

    assert "## Trigger Reason / Mode / Policy Zone / Risk" in template


def test_template_resolver_raises_for_unknown_template_id():
    resolver = PRTemplateResolver()

    with pytest.raises(UnknownPRTemplateError):
        resolver.resolve("PRT.UNKNOWN")
