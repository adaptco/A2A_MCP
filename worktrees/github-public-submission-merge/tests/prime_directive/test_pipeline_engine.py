import pytest
from src.prime_directive.pipeline.engine import PipelineEngine

def test_pipeline_engine_execution():
    pipeline = PipelineEngine()

    def step1(context):
        context['step1'] = True
        return context

    def step2(context):
        context['step2'] = True
        return context

    pipeline.add_step(step1)
    pipeline.add_step(step2)

    result = pipeline.execute({})
    assert result['step1'] is True
    assert result['step2'] is True
