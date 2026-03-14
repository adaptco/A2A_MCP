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
    workflow_text = (WORKFLOWS_DIR / 'main.yml').read_text(encoding='utf-8')
    assert '/plans/ingress' in workflow_text


def test_push_knowledge_comment_step_is_guarded_and_uses_issue_permission():
    workflow_file = WORKFLOWS_DIR / 'push_knowledge.yml'
    if not workflow_file.exists():
        return

    workflow = _load_workflow('push_knowledge.yml')
    comment_script = workflow_file.read_text(encoding='utf-8')

    assert workflow['jobs']['ingest-and-embed']['permissions']['issues'] == 'write'
    assert 'if (!issue_number)' in comment_script
    assert 'skipping ingestion receipt comment' in comment_script
    assert 'await github.rest.issues.createComment' in comment_script


def test_agents_ci_cd_notifies_cicd_monitor():
    workflow = _load_workflow('agents-ci-cd.yml')
    monitor_job = workflow['jobs']['notify-cicd-monitor']

    assert monitor_job['if'] == 'always()'
    workflow_text = (WORKFLOWS_DIR / 'agents-ci-cd.yml').read_text(encoding='utf-8')
    assert '/webhooks/github/actions' in workflow_text
    assert 'X-GitHub-Event: workflow_run' in workflow_text
    assert 'X-Hub-Signature-256' in workflow_text


def test_integration_workflow_is_valid_and_runs_postgres_backed_tests():
    workflow = _load_workflow('integration_test.yml')

    assert workflow['permissions']['contents'] == 'read'
    assert 'postgres' in workflow['jobs']['test']['services']
    workflow_text = (WORKFLOWS_DIR / 'integration_test.yml').read_text(encoding='utf-8')
    assert 'tests/test_storage.py' in workflow_text
    assert 'tests/test_mcp_agents.py' in workflow_text


def test_cicd_monitor_hook_tracks_key_workflows():
    workflow = _load_workflow('cicd-monitor.yml')
    trigger = workflow.get('on', workflow.get(True))
    watched = trigger['workflow_run']['workflows']
    workflow_text = (WORKFLOWS_DIR / 'cicd-monitor.yml').read_text(encoding='utf-8')

    assert 'Agents CI/CD' in watched
    assert 'Python application' in watched
    assert 'A2A-MCP Integration Tests' in watched
    assert 'X-Hub-Signature-256' in workflow_text


def test_release_gke_workflow_has_readiness_gate_and_webhook():
    workflow = _load_workflow('release-gke-deploy.yml')
    workflow_text = (WORKFLOWS_DIR / 'release-gke-deploy.yml').read_text(encoding='utf-8')

    trigger = workflow.get('on', workflow.get(True))
    assert 'workflow_dispatch' in trigger
    assert 'push' in trigger
    assert 'tags' in trigger['push']
    assert workflow['permissions']['contents'] == 'read'
    assert 'preflight' in workflow['jobs']
    assert 'deploy' in workflow['jobs']
    assert 'notify' in workflow['jobs']
    assert '/cicd/status/' in workflow_text
    assert '/webhooks/github/actions' in workflow_text
    assert 'X-Hub-Signature-256' in workflow_text
