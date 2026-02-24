import functions_framework
from google.cloud import bigtable
from google.cloud.bigtable import row_filters
import json
import os

# Configuration
PROJECT_ID = os.environ.get("PROJECT_ID")
INSTANCE_ID = os.environ.get("BIGTABLE_INSTANCE", "main-instance")
TABLE_ID = os.environ.get("BIGTABLE_TABLE", "user-profiles")

# Initialize Bigtable Client
client = bigtable.Client(project=PROJECT_ID, admin=True)
instance = client.instance(INSTANCE_ID)
table = instance.table(TABLE_ID)

@functions_framework.http
def query_bigtable(request):
    """
    HTTP Cloud Function to be used as a Vertex AI Agent Tool.
    Expects JSON: {"row_key": "user_123"}
    """
    try:
        request_json = request.get_json(silent=True)
        
        if not request_json or 'row_key' not in request_json:
            return (json.dumps({"error": "Missing 'row_key' parameter"}), 400)

        row_key = request_json['row_key']
        
        # Fetch row from Bigtable
        row = table.read_row(row_key.encode('utf-8'))

        if not row:
            return (json.dumps({"message": "No data found for this key"}), 200)

        # Parse row data into a friendly JSON format
        data = {}
        for family, columns in row.cells.items():
            family_str = family
            data[family_str] = {}
            for column, cells in columns.items():
                # Decode column name and value (taking the latest version)
                col_name = column.decode('utf-8')
                val = cells[0].value.decode('utf-8')
                data[family_str][col_name] = val

        return (json.dumps({
            "row_key": row_key,
            "data": data
        }), 200)

    except Exception as e:
        return (json.dumps({"error": str(e)}), 500)