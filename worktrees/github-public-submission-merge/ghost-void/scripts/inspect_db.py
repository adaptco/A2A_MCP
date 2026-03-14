import sqlite3
import pandas as pd
import sys
import os

# Add project root to sys.path to resolve imports if necessary
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def inspect_artifacts():
    # Connect to the local SQLite database
    # Adjust 'a2a_mcp.db' if your database name is different in storage.py
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'a2a_mcp.db')
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found at {db_path}")
        return

    try:
        conn = sqlite3.connect(db_path)
        
        # Check if table exists
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='artifacts'")
        if not cursor.fetchone():
            print("📭 Table 'artifacts' does not exist in the database.")
            conn.close()
            return

        query = "SELECT * FROM artifacts ORDER BY created_at DESC"
        df = pd.read_sql_query(query, conn)
        
        if df.empty:
            print("📭 No artifacts found in the database yet.")
        else:
            print(f"📂 Found {len(df)} artifacts:")
            # Display available columns to be safe
            cols = [c for c in ['id', 'type', 'agent_name', 'created_at'] if c in df.columns]
            print(df[cols].to_string(index=False))
            
            # Show the most recent content
            print("\n📝 Most Recent Artifact Content:")
            print("-" * 30)
            if 'content' in df.columns:
                print(df.iloc[0]['content'])
            else:
                print("No 'content' column found.")
            print("-" * 30)
        
        conn.close()
    except Exception as e:
        print(f"❌ Error inspecting database: {e}")

if __name__ == "__main__":
    inspect_artifacts()
