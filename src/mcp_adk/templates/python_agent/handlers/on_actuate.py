def handle(payload: dict) -> dict:
    return {"status": "ok", "event": "actuate", "payload": payload}
