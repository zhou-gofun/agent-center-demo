# Agent Center 流程说明

## 架构概览

```
用户请求
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│  Flask API (src/api/routes.py)                                    │
│  - /v1/chat - 统一入口                                          │
│  - DEBUG_MODE=True 时打印详细日志                                 │
└─────────────────────────────────────────────────────────────────┘
    │
    ├──────── 步骤1: 知识库搜索 ─────────────┐
    │                                        │
    ▼                                        ▼
┌──────────────────────┐      ┌──────────────────────┐
│  ChromaDB 向量搜索      │      │  步骤2: 路由决策       │
│  - assembly_tools     │      │  routing_agent       │
│  - literature         │      │  - 分析意图            │
└──────────────────────┘      │  - 决定目标 agent      │
                                 │  └─────────────────────┘
    │                                        │
    ▼                                        ▼
┌──────────────────────────────────────────────────────────────────┐
│                        步骤3: Agent 执行                            │
│  conversation_orchestrator_agent / pipeline_agent / data_analyst_agent│
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ _build_skill_context() - 执行 skills                         │  │
│  │  ┌──────────────────────────────────────────────────────┐   │  │
│  │  │ semantic-search __init__.py → execute()            │   │  │
│  │  │ tool-matcher __init__.py → execute()               │   │  │
│  │  └──────────────────────────────────────────────────────┘   │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                   │
│  → LLM Chat (system_prompt + skill_results + user_query)          │
└──────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│  步骤4: 响应返回                                                   │
│  - response: LLM 生成的回答                                      │
│  - agent_used: 实际调用的 agent                                 │
│  - execution_time: 执行时间                                       │
│  - debug: 调试信息（如果启用）                                   │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
用户收到响应
```

## 详细执行流程

### 1. 用户发送请求
```bash
POST /v1/chat
{
  "query": "如何做差异分析，需要考虑哪些细节？",
  "context": {
    "data_summary": "...",  # 可选
    "conversation_history": [...]  # 可选
  }
}
```

### 2. 知识库搜索（可选）
```python
# 搜索 ChromaDB 中的相关内容
db.search("assembly_tools", query, top_k=3)
db.search("literature", query, top_k=3)
```

**调试输出示例:**
```
🔍 Searching knowledge base...
   Collections: ['assembly_tools', 'literature']
   assembly_tools: 3 results
   literature: 2 results
✓ Total search results: 5
```

### 3. 路由决策
```python
# 调用 routing_agent 决定使用哪个 agent
executor.execute_agent('routing_agent', {...})
```

**调试输出示例:**
```
🔀 ROUTING DECISION
──────────────────────────────────────────
Routing response:
   {"action": "route_to_agent", "target": "conversation_orchestrator_agent", ...}

🎯 Parsed routing decision:
   Action: route_to_agent
   Target: conversation_orchestrator_agent
   Reasoning: 用户询问分析方法，需要通过对话收集更多信息
```

### 4. Agent 执行
```python
# 调用目标 agent
executor.execute_agent('conversation_orchestrator_agent', {...})
```

**内部流程:**
```
┌──────────────────────────────────────────────────────────────┐
│ conversation_orchestrator_agent                              │
│  skills: [semantic-search, tool-matcher]                     │
└──────────────────────────────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────────────────────────────┐
│ _build_skill_context(skills, input_data)                      │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ 🔧 EXECUTING SKILL: semantic-search                     │  │
│  │ ────────────────────────────────────────────────────────│  │
│  │ 📥 Input: ['query']                                       │  │
│  │ 📤 Output: 5 search results                               │  │
│  │      - Independent t-test (score: 0.92)                    │  │
│  │      - ANOVA (score: 0.87)                               │  │
│  │ ────────────────────────────────────────────────────────│  │
│  └────────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ 🔧 EXECUTING SKILL: tool-matcher                        │  │
│  │ ────────────────────────────────────────────────────────│  │
│  │ 📥 Input: ['query']                                       │  │
│  │ 📤 Output: 4 matched tools                                │  │
│  │      - t-test (score: 0.95)                               │  │
│  │      - Mann-Whitney U (score: 0.78)                       │  │
│  │ ────────────────────────────────────────────────────────│  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────────────────────────────┐
│ LLM Chat                                                        │
│  system_prompt: skill_results + agent_prompt                   │
│  user_message: user_query                                      │
└──────────────────────────────────────────────────────────────┘
    │
    ▼
LLM Response
```

### 5. 返回响应
```json
{
  "success": true,
  "data": {
    "response": "根据您的问题...",
    "agent_used": "conversation_orchestrator_agent",
    "execution_time": 3.45,
    "debug": {
      "agents_called": ["routing_agent", "conversation_orchestrator_agent"],
      "search_results_count": 5,
      "steps": [
        {"step": "request_received", "time": 0.0},
        {"step": "knowledge_search", "time": 0.23},
        {"step": "routing", "time": 0.89},
        {"step": "target_execution", "time": 2.33}
      ]
    }
  }
}
```

## 调试输出说明

启用 `DEBUG_MODE=True` 后，控制台会打印：

```
████████████████████████████████████████████████
📥 REQUEST RECEIVED
████████████████████████████████████████████████
Query: 如何做差异分析，需要考虑哪些细节？
Context keys: []

🔍 Searching knowledge base...
   Collections: ['assembly_tools', 'literature']
   assembly_tools: 3 results
   literature: 2 results
✓ Total search results: 5

🔀 ROUTING DECISION
──────────────────────────────────────────
Routing response:
   {"action": "route_to_agent", "target": "conversation_orchestrator_agent", ...}

🎯 Parsed routing decision:
   Action: route_to_agent
   Target: conversation_orchestrator_agent
   Reasoning: 用户询问分析方法，需要通过对话收集更多信息

████████████████████████████████████████████████
🚀 CALLING TARGET AGENT: conversation_orchestrator_agent
████████████████████████████████████████████████

────────────────────────────────────────
🔧 EXECUTING SKILL: semantic-search
────────────────────────────────────────
📥 Input: ['query']
📤 Output: 5 search results
      - Independent t-test (score: 0.92)
      - ANOVA (score: 0.87)
────────────────────────────────────────

────────────────────────────────────────
🔧 EXECUTING SKILL: tool-matcher
────────────────────────────────────────
📥 Input: ['query']
📤 Output: 4 matched tools
      - t-test (score: 0.95)
      - Mann-Whitney U (score: 0.78)
────────────────────────────────────────

✓ Target agent response received
   Response length: 856 chars

████████████████████████████████████████████████
✅ REQUEST COMPLETE
████████████████████████████████████████████████
Agent used: conversation_orchestrator_agent
Total time: 3.456s
Agents called: routing_agent → conversation_orchestrator_agent
████████████████████████████████████████████████
```

## 测试方法

### 方法1: 运行测试脚本
```bash
python test_flow.py
```

### 方法2: 使用 curl
```bash
# 简单查询
curl -X POST http://localhost:8000/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "如何做差异分析？"}'

# 带数据摘要
curl -X POST http://localhost:8000/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "分析我的数据", "context": {"data_summary": "..."}}'
```

### 方法3: Python 请求
```python
import requests

response = requests.post("http://localhost:8000/v1/chat", json={
    "query": "如何做差异分析？",
    "context": {}
})

result = response.json()
print(result["data"]["response"])
print(result["data"]["debug"])  # 调试信息
```

## 调试控制接口

```bash
# 查看调试状态
curl http://localhost:8000/v1/debug/status

# 切换调试模式
curl -X POST http://localhost:8000/v1/debug/toggle
```
