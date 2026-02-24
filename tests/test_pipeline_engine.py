import pytest
from src.prime_directive.pipeline.engine import PipelineEngine

@pytest.mark.asyncio
async def test_pipeline_engine_basic_flow():
    engine = PipelineEngine()

    pipeline_def = {
        "stages": [
            {"name": "stage1", "action": "do_something"},
            {"name": "stage2", "action": "do_something_else"}
        ]
    }

    result = await engine.run_pipeline(pipeline_def, context={"initial": "data"})

    assert result["status"] == "success"
    assert "stage1" in result["results"]
    assert "stage2" in result["results"]
    assert result["results"]["stage1"]["output"] == "Executed action: do_something"

@pytest.mark.asyncio
async def test_pipeline_engine_context_propagation():
    engine = PipelineEngine()

    pipeline_def = {
        "stages": [
            {"name": "stage1", "action": "generate_output"}
        ]
    }

    result = await engine.run_pipeline(pipeline_def, context={"foo": "bar"})

    # context is updated with result
    assert result["final_context"]["foo"] == "bar"
    assert result["final_context"]["status"] == "completed"
