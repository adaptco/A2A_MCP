import sqlite3
    import pandas as pd
    from schemas.database import ArtifactModel
    
    def inspect_artifacts():
        # Connect to the local SQLite database
        # Adjust 'a2a_mcp.db' if your database name is different in storage.py
        conn = sqlite3.connect('a2a_mcp.db')
        
        query = "SELECT * FROM artifacts ORDER BY created_at DESC"
        df = pd.read_sql_query(query, conn)
        
        if df.empty:
            print("📭 No artifacts found in the database yet.")
        else:
            print(f"📂 Found {len(df)} artifacts:")
            print(df[['id', 'type', 'agent_name', 'created_at']].to_string(index=False))
            
            # Show the most recent content
            print("
📝 Most Recent Artifact Content:")
            print("-" * 30)
            print(df.iloc[0]['content'])
            print("-" * 30)
        
        conn.close()
    
    if __name__ == "__main__":
        inspect_artifacts()
    
