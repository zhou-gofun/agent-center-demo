# Agent Center

通用 Agent 中心服务，采用 Claude Code 的 subagent 和 skill 技术架构。

## 特性

- **动态管理**：运行时创建/更新/删除 agents 和 skills
- **远程调用**：通过 Flask API 触发 agent/skill 执行
- **LLM 集成**：使用 Qwen API (OpenAI 兼容模式)
- **知识库集成**：向量语义搜索（ChromaDB）

## 目录结构

```
/mnt/d/temp/proj/agent_center/
├── src/
│   ├── main.py                      # Flask 应用入口
│   ├── config.py                    # 配置管理
│   ├── core/                        # 核心框架层
│   │   ├── llm_client.py            # Qwen LLM 客户端
│   │   ├── agent_manager.py         # Agent 管理器
│   │   ├── skill_manager.py         # Skill 管理器
│   │   └── executor.py              # 执行引擎
│   ├── vector_db/                   # 向量数据库层
│   │   ├── chroma_store.py          # ChromaDB 实现
│   │   ├── embeddings.py            # Embedding 生成
│   │   └── data_loader.py           # Excel 数据加载
│   ├── registry/                    # Agent/Skill 注册表
│   │   ├── agents/                  # 运行时 agent 文件
│   │   └── skills/                  # 运行时 skill 文件
│   ├── api/                         # API 层
│   │   └── routes.py                # REST API 端点
│   └── utils/
│       └── logger.py                # 日志工具
├── config/                          # 配置定义
│   ├── agents.yaml                  # Agent 定义
│   └── skills.yaml                  # Skill 定义
├── data/                            # 数据目录
│   └── vector_store/                # ChromaDB 持久化
├── requirements.txt
└── .env.example
```

## 安装

```bash
# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入 Qwen API Key
```

## 运行

```bash
cd /mnt/d/temp/proj/agent_center
python -m src.main
```

服务将在 `http://0.0.0.0:8000` 启动。

## API 接口

### Agent 执行

```bash
POST /v1/agent/<agent_name>/execute
Content-Type: application/json

{
  "input": {
    "query": "用户问题"
  }
}
```

### 知识库搜索

```bash
POST /v1/knowledge/search
Content-Type: application/json

{
  "query": "搜索文本",
  "collection": "assembly_tools",
  "top_k": 10
}
```

### 流程生成

```bash
POST /v1/pipeline/generate
Content-Type: application/json

{
  "summary": "数据摘要",
  "query": "用户需求"
}
```

### 注册表管理

```bash
# 列出所有 agents
GET /v1/registry/agents

# 注册新 agent
POST /v1/registry/agents
{
  "name": "new-agent",
  "config": {...}
}

# 列出所有 skills
GET /v1/registry/skills
```

## 配置文件

### Agent 定义 (`config/agents.yaml`)

```yaml
agents:
  pipeline_agent:
    name: pipeline-agent
    description: 流程组配专家
    tools: [Read, Grep]
    skills: [semantic-search, tool-matcher]
    prompt: |
      You are a pipeline generation expert...
```

### Skill 定义 (`config/skills.yaml`)

```yaml
skills:
  semantic_search:
    name: semantic-search
    description: 向量语义搜索
    allowed-tools: [Read]
    instructions: |
      Perform semantic search...
```

## 环境变量

- `QWEN_KEY`: Qwen API Key
- `QWEN_URL`: Qwen API URL
- `FLASK_HOST`: Flask 服务地址
- `FLASK_PORT`: Flask 服务端口
- `VECTOR_DB_PATH`: 向量数据库存储路径
