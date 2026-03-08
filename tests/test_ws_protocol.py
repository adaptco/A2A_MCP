from fastapi.testclient import TestClient

from prime_directive.api.app import app


def test_health_endpoint():
    client = TestClient(app)
    response = client.get('/health')
    assert response.status_code == 200


def test_pipeline_websocket_supports_protocol_messages():
    client = TestClient(app)

    with client.websocket_connect('/ws/pipeline') as websocket:
        initial_event = websocket.receive_json()
        assert initial_event == {'type': 'state.transition', 'state': 'idle'}

        websocket.send_json({'type': 'ping'})
        assert websocket.receive_json() == {'type': 'pong'}

        websocket.send_json({'type': 'get_state'})
        assert websocket.receive_json() == {'type': 'state.transition', 'state': 'idle'}

        websocket.send_json({'type': 'render_request'})
        assert websocket.receive_json() == {'type': 'ack', 'message': 'render_request received'}

        websocket.send_json({'type': 'unknown'})
        assert websocket.receive_json() == {'type': 'error', 'message': 'unknown message type'}
