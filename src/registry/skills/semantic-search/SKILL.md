---
name: semantic-search
description: 向量语义搜索，在知识库中检索相关工具和文献
allowed-tools: [Read]
context: inline
---

# Semantic Search

Perform vector-based semantic search across knowledge bases to find relevant tools and literature.

# Semantic Search

Perform vector-based semantic search across knowledge bases to find relevant tools and literature.

## When to Use

Use this skill when:
- Searching for statistical tools based on analysis requirements
- Looking up literature based on research topics
- Finding relevant methods beyond keyword matching
- Query is descriptive rather than exact terms

## Available Collections

### assembly_tools
Statistical analysis tools and methods.

**Use for:**
- Finding tools for specific statistical tests
- Discovering analysis methods for research designs
- Matching tools to data characteristics

**Metadata includes:**
- `toolid`: Unique tool identifier
- `toolname`: Display name of the tool
- `idname`: Tool identifier string
- `description`: What the tool does
- `keywords`: Search keywords
- `applications`: Usage scenarios

### literature
Medical literature and research papers.

**Use for:**
- Finding relevant research papers
- Discovering analysis methods from literature
- Evidence-based method selection

## Using the Script

```bash
# Search in a specific collection
python src/registry/skills/semantic_search/scripts/search.py \
  --query "compare two groups" \
  --collection assembly_tools \
  --top-k 5

# Search across all collections
python src/registry/skills/semantic_search/scripts/search.py \
  --query "survival analysis methods"
```

Or as a module:

```python
from src.registry.skills.semantic_search.scripts.search import semantic_search

result = semantic_search(
    query="compare treatment groups",
    collection="assembly_tools",
    top_k=5
)
```

## Output Format

```json
{
  "query": "compare treatment groups",
  "results": [
    {
      "id": "tool_123",
      "collection": "assembly_tools",
      "toolid": 123,
      "toolname": "Independent t-test",
      "idname": "t_test_independent",
      "description": "Compare means between two independent groups",
      "score": 0.92,
      "metadata": {...}
    }
  ],
  "collection": "assembly_tools",
  "count": 5
}
```

## Relevance Scoring

Results are ranked by semantic similarity:
- **≥ 0.8**: Highly relevant - exact or very close match
- **0.6 - 0.8**: Relevant - related concepts
- **0.4 - 0.6**: Somewhat relevant - tangentially related
- **< 0.4**: Not relevant - likely unrelated

## Integration

This skill is used by:
- **literature-matcher**: For finding similar studies
- **pipeline-agent**: For discovering relevant tools

## Technical Notes

The semantic search uses:
- Vector embeddings for meaning-based matching
- Cosine similarity for scoring
- ChromaDB for vector storage
- Automatic collection discovery
