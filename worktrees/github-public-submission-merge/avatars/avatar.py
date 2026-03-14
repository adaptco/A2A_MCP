import asyncio
import json
import websockets

class Avatar:
    def __init__(self, uri="ws://localhost:8080"):
        self.uri = uri
        self.websocket = None
        self.is_connected = False
        self.state = {}

    async def connect(self):
        """Establishes a WebSocket connection to the game engine."""
        try:
            self.websocket = await websockets.connect(self.uri)
            self.is_connected = True
            print(f"[Avatar] Connected to {self.uri}")
            # Start the background task to listen for state updates
            asyncio.create_task(self._listen())
        except Exception as e:
            print(f"[Avatar] Connection failed: {e}")
            self.is_connected = False

    async def disconnect(self):
        """Closes the WebSocket connection."""
        if self.websocket:
            await self.websocket.close()
            self.is_connected = False
            print("[Avatar] Disconnected.")

    async def _listen(self):
        """Background loop to receive and parse engine state updates."""
        try:
            async for message in self.websocket:
                try:
                    self.state = json.loads(message)
                except json.JSONDecodeError:
                    # Engine stdout might not always be JSON
                    pass
        except websockets.exceptions.ConnectionClosed:
            self.is_connected = False
            print("[Avatar] Connection closed by server.")

    async def send_command(self, action, payload=None):
        """Sends a JSON-formatted command to the engine."""
        if not self.is_connected:
            print("[Avatar] Warning: Not connected. Command ignored.")
            return

        command = {"action": action}
        if payload:
            command.update(payload)
        
        await self.websocket.send(json.dumps(command))

    async def move(self, direction: float):
        """Moves the avatar: 1.0 for right, -1.0 for left, 0.0 for stop."""
        await self.send_command("move", {"direction": direction})

    async def jump(self):
        """Triggers a jump action."""
        await self.send_command("jump")

    async def shoot(self):
        """Triggers a shoot action."""
        await self.send_command("shoot")

    def get_position(self):
        """Returns the last known position from engine state."""
        return self.state.get("position", {"x": 0, "y": 0})

    def get_state(self):
        """Returns the full state dictionary."""
        return self.state
