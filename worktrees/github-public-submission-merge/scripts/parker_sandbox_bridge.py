"""
Parker's Sandbox Bridge: Mario Kart Physics Emulation
Integrates Base44 World Model with Supra Drift Logic to simulate race dynamics.
"""

import sys
import os
import time

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from phase_space_tick import PhaseSpaceTick

def run_simulation():
    ticker = PhaseSpaceTick()
    
    # Mario Kart Race Sequence
    race_sequence = [
        ("Start Line - Green Light", 0.0, 0.0),
        ("Acceleration Boost", 15.0, 0.0),
        ("First Corner Entry", 25.0, 0.1),
        ("Hairpin Drift - Apex", 35.0, 0.7),  # High drift event
        ("Hairpin Exit - Counter", 32.0, -0.4), # Counter-steer
        ("Straightaway Turbo", 45.0, 0.0),
        ("Chicane Left", 38.0, 0.3),
        ("Chicane Right", 38.0, -0.3),
        ("Final Lap - Blue Shell", 10.0, 0.0), # Sudden slow down
        ("Finish Line Cross", 40.0, 0.0)
    ]

    print("\n🏁 --- WELCOME TO PARKER'S SANDBOX --- 🏁")
    print("Emulating Mario Kart Physics on Base44 Grid...\n")
    time.sleep(1)

    for step, (event, velocity, steering) in enumerate(race_sequence):
        print(f"\n[{step+1}/{len(race_sequence)}] EVENT: {event}")
        
        # Run Phase Space Tick
        result = ticker.run_tick(
            prompt=f"Simulate {event}", 
            velocity=velocity, 
            steering=steering, 
            verbose=False # Custom bridge visualization
        )
        
        # Bridge Visualization
        drift = result["drift"]
        
        if drift:
            mode_icon = "🟢" if drift.mode == "GRIP" else ("🟡" if drift.mode == "SLIP" else "🔥")
            mode_str = drift.mode
            score = drift.drift_score
        else:
            mode_icon = "⚪"
            mode_str = "STATIC"
            score = 0.0
        
        print(f"   🏎️  Speed: {velocity:.1f} m/s | Steer: {steering:.2f} rad")
        print(f"   📊 Physics: {mode_icon} {mode_str} (Score: {score:.2f})")
        
        grid_pos = result["grid_pos"]
        region = "ORDER (Center)"
        
        if drift:
            if drift.mode == "DRIFT":
                region = "FLUX (Edge)"
            elif drift.mode == "SLIP":
                region = "RING (Mid)"
            
        print(f"   🗺️  Map: {grid_pos} -> {region}")
        
        # ASCII Mini-Map
        ticker.grid.print_grid()
        time.sleep(0.5)

    print("\n🏁 --- RACE COMPLETE --- 🏁")

if __name__ == "__main__":
    run_simulation()
