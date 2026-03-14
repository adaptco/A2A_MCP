# ToolQuest Semantic Search

Semantic tool discovery for ToolQuest Pro using vector embeddings.

## Quick Start

### 1. Start Services

```bash
cd toolquest/semantic
docker-compose up -d
```

### 2. Index Sample Tools

```bash
python embedding_pipeline.py
```

### 3. Test Search API

```bash
# Start API (if not using Docker)
python semantic_search_api.py

# Test search
curl -X POST http://localhost:8001/api/semantic/search \
  -H "Content-Type: application/json" \
  -d '{"query_text": "find large files", "limit": 5}'
```

## Architecture

- **schemas.py**: Pydantic models for tools, work orders, challenges
- **embedding_pipeline.py**: Generate embeddings using sentence-transformers
- **semantic_search_api.py**: FastAPI endpoints for search
- **docker-compose.yml**: Qdrant + API services

## API Endpoints

### `POST /api/semantic/search`

Search for tools using natural language.

**Request:**

```json
{
  "query_text": "search for patterns in files",
  "category_filter": ["text-processing"],
  "difficulty_filter": [1, 2, 3],
  "limit": 10
}
```

**Response:**

```json
[
  {
    "tool": {
      "tool_id": "grep_001",
      "tool_name": "grep",
      "description": "Search for patterns...",
      "similarity_score": 0.89,
      "rank": 1
    }
  }
]
```

### `GET /api/tools/{tool_id}/similar`

Find similar tools.

## Next Steps

1. **UI Integration**: Add Discovery Mode to ToolQuest frontend
2. **Challenge Generation**: Implement AI challenge system
3. **Leaderboard**: Track semantic exploration metrics
