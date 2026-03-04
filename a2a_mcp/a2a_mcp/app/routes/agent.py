from fastapi import APIRouter

from ..schemas.website_agent import WebsiteTemplate, WebsiteTemplateRequest
from ..services.website_builder_agent import WebsiteBuilderTemplateAgent

router = APIRouter(prefix="/agent", tags=["agent"])
_agent = WebsiteBuilderTemplateAgent()


@router.post("/website-template", response_model=WebsiteTemplate)
async def website_template(request: WebsiteTemplateRequest) -> WebsiteTemplate:
    """Generate a normalized website-builder template from chat artifacts."""

    return _agent.generate_template(request)
