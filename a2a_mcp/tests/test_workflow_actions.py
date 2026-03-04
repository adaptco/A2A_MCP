from pathlib import Path

import yaml


WORKFLOWS_DIR = Path('.github/workflows')


def _load_workflow(name: str) -> dict:
    return yaml.safe_load((WORKFLOWS_DIR / name).read_text(encoding='utf-8'))


def test_agents_ci_cd_release_upload_has_write_permission():
    workflow = _load_workflow('agents-ci-cd.yml')

    assert workflow['permissions']['contents'] == 'read'
    assert workflow['jobs']['deploy-release-contracts']['permissions']['contents'] == 'write'


def test_main_workflow_can_comment_on_issues():
    workflow = _load_workflow('main.yml')

    assert workflow['permissions']['contents'] == 'read'
    assert workflow['permissions']['issues'] == 'write'


def test_push_knowledge_comment_step_is_guarded_and_uses_issue_permission():
    workflow = _load_workflow('push_knowledge.yml')
    comment_script = (WORKFLOWS_DIR / 'push_knowledge.yml').read_text(encoding='utf-8')

    assert workflow['jobs']['ingest-and-embed']['permissions']['issues'] == 'write'
    assert 'if (!issue_number)' in comment_script
    assert 'skipping ingestion receipt comment' in comment_script
    assert 'await github.rest.issues.createComment' in comment_script
