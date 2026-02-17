import sqlite3

import pandas as pd


def inspect_artifacts() -> None:
    conn = sqlite3.connect("a2a_mcp.db")
    query = "SELECT * FROM artifacts ORDER BY created_at DESC"
    df = pd.read_sql_query(query, conn)

    if df.empty:
        print("No artifacts found in the database yet.")
    else:
        print(f"Found {len(df)} artifacts:")
        cols = [c for c in ["id", "type", "agent_name", "created_at"] if c in df.columns]
        if cols:
            print(df[cols].to_string(index=False))

        if "content" in df.columns:
            print("\nMost recent artifact content:")
            print("-" * 30)
            print(df.iloc[0]["content"])
            print("-" * 30)

    conn.close()


if __name__ == "__main__":
    inspect_artifacts()
