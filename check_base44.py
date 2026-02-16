
import sys
import os

# Add current directory to path
sys.path.append(os.getcwd())

try:
    from base44.grid import Base44Grid
    grid = Base44Grid()
    print(f"Grid created. Cells: {len(grid.list_cells())}")
    
    # Check a cell
    c = grid.get_cell(0)
    print(f"Cell 0: {c}")
    
    print("Basic check passed.")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
