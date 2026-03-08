import asyncio
import websockets
import json
import random
import sys
import time
import argparse

async def speed_run(uri="ws://localhost:8080", simulate=False):
    # MALTA SCALE CONSTANTS
    # Length: ~27km (27,000m)
    # Circumference drive time (car): ~1.5 hours
    # Target: Traverse 27km in ~1.5 hours implies ~18 km/h (5 m/s) maintained speed.
    TOTAL_DISTANCE_METERS = 27000 
    MAX_SPEED_MPS = 6.0  # ~21.6 km/h (Marathon pace)
    
    # Time Compression: We want to watch the 1.5 hour run in about 30 seconds.
    # 1.5 hours = 5400 seconds.
    # 5400 / 30 = 180x speedup.
    TIME_COMPRESSION = 200 
    
    print(f"🔥 SPEED RUNNER INITIALIZED. TARGET: {uri} {'(SIMULATION)' if simulate else ''}")
    print(f"🌍 MAP SCALE: MALTA (Length: {TOTAL_DISTANCE_METERS/1000}km)")
    print(f"🏃 PHYSICS RESTRICTIONS: Max Speed {MAX_SPEED_MPS} m/s ({MAX_SPEED_MPS*3.6:.1f} km/h)")
    print(f"⏩ TIME COMPRESSION: {TIME_COMPRESSION}x (1 sec real = {TIME_COMPRESSION} sec game)")
    print("🚀 3... 2... 1... GO!")
    
    # Mock context manager for simulation
    class MockSocket:
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def send(self, msg): pass
        async def recv(self): return "{}"
    
    connector = websockets.connect(uri) if not simulate else MockSocket()
    
    try:
        async with connector as websocket:
            # Init
            if not simulate:
                 await websocket.send(json.dumps({"type": "init", "role": "speed_runner"}))
            
            # Physics State
            distance = 0.0
            game_time = 0.0
            real_start_time = time.time()
            
            # Narrative Checkpoints
            checkpoints = {
                5000: "🏙️  VALLETTA CITY GATES PASSED",
                10000: "🪵  BUSKETT GARDENS TRAVERSED",
                15000: "🏖️  GOLDEN BAY BEACH (Halfway Point)",
                20000: "🏰  MDINA WALLS SCALED",
                25000: "⛴️  CIRKEWWA FERRY TERMINAL IN SIGHT"
            }
            next_checkpoint = min(checkpoints.keys())

            while distance < TOTAL_DISTANCE_METERS:
                # dt is the game-time delta per loop iteration
                # We aim for ~30 fps update in real time
                real_dt = 0.033
                dt = real_dt * TIME_COMPRESSION
                
                game_time += dt
                
                # Physics: Accelerate to max speed
                current_speed = MAX_SPEED_MPS
                
                # Random "terrain" slowdowns
                if random.random() < 0.05:
                    current_speed *= 0.8 # Rough terrain / uphill
                
                distance += current_speed * dt
                
                # Check checkpoints
                if next_checkpoint and distance >= next_checkpoint:
                    print(f"📍 {checkpoints[next_checkpoint]}")
                    # Find next checkpoint
                    remaining = [k for k in checkpoints.keys() if k > distance]
                    next_checkpoint = remaining[0] if remaining else None

                # Periodic Logging (every ~15 game minutes)
                if int(game_time) % 900 < int(game_time - dt) % 900:
                    completion = (distance / TOTAL_DISTANCE_METERS) * 100
                    print(f"⏱️  Game Time: {int(game_time//60)}m | Dist: {distance/1000:.1f}km ({completion:.1f}%) | Pace: {current_speed*3.6:.1f} km/h")
                
                if not simulate:
                     action = {
                        "type": "move_to",
                        "distance": distance,
                        "timestamp": game_time
                    }
                     await websocket.send(json.dumps(action))

                await asyncio.sleep(real_dt)
            
            total_real_time = time.time() - real_start_time
            print(f"\n🏁 RUN COMPLETE! 🏆")
            print(f"🌍 Distance Covered: {distance/1000:.2f} km")
            print(f"⏱️  Total Game Time: {int(game_time//60)} mins {int(game_time%60)} secs")
            print(f"👀 Real Watch Time: {total_real_time:.2f} seconds")

    except (ConnectionRefusedError, OSError) as e:
        if not simulate:
            print(f"❌ Could not connect to {uri}. Is the game server running?")
            print("\n⚠️  SWITCHING TO SIMULATION MODE for demonstration...")
            await asyncio.sleep(1)
            await speed_run(uri, simulate=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("uri", nargs="?", default="ws://localhost:8080")
    parser.add_argument("--simulate", action="store_true")
    args = parser.parse_args()
    
    try:
        asyncio.run(speed_run(args.uri, simulate=args.simulate))
    except KeyboardInterrupt:
        print("\n🏁 RUN COMPLETE. NEW RECORD?")
