# Agent Center

通用 Agent 中心服务，采用 Claude Code 的 subagent 和 skill 技术架构。

## 特性

- **Skill 自动发现**：添加新 skill 后自动生效，无需手动配置
- **动态管理**：运行时创建/更新/删除 agents 和 skills
- **远程调用**：通过 Flask API 触发 agent/skill 执行
- **LLM 集成**：使用 Qwen API (OpenAI 兼容模式)
- **知识库集成**：向量语义搜索（ChromaDB）
- **通用脚本执行**：支持 Python 脚本技能，无需模块导入

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
│   │   ├── executor.py              # 执行引擎
│   │   ├── registry_scanner.py      # 注册表扫描器（新增）
│   │   ├── universal_executor.py    # 通用脚本执行器（新增）
│   │   ├── execution_orchestrator.py# 执行编排器
│   │   └── python_script_executor.py# Python 脚本执行器
│   ├── vector_db/                   # 向量数据库层
│   │   ├── chroma_store.py          # ChromaDB 实现
│   │   ├── embeddings.py            # Embedding 生成
│   │   └── data_loader.py           # Excel 数据加载
│   ├── registry/                    # Agent/Skill 注册表
│   │   ├── agents/                  # Agent 定义 (.md 文件)
│   │   │   ├── routing-agent.md
│   │   │   ├── general-purpose-agent.md
│   │   │   ├── pipeline-agent.md
│   │   │   └── data-analyst-agent.md
│   │   └── skills/                  # Skill 定义 (SKILL.md + 脚本)
│   │       ├── semantic-search/     # 语义搜索
│   │       ├── tool-matcher/        # 工具匹配
│   │       ├── pipeline-decision/   # 流程决策
│   │       ├── question-generator/  # 问题生成
│   │       ├── literature-matcher/  # 文献匹配
│   │       ├── data-analyzer/       # 数据分析
│   │       └── weather-query/       # 天气查询（新增）
│   ├── api/                         # API 层
│   │   └── routes.py                # REST API 端点
│   └── utils/
│       └── logger.py                # 日志工具
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
python src/main.py
```

服务将在 `http://0.0.0.0:5000` 启动。

## API 接口

### 智能聊天（路由模式）

```bash
POST /v1/chat
Content-Type: application/json

{
  "query": "今天成都的天气怎么样？"
}
```

系统会自动路由到合适的 agent 处理。

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

# 列出所有 skills
GET /v1/registry/skills

# 扫描注册表
GET /v1/registry/scan
```

## Skill 自动发现机制

添加新 skill 只需两步：

### 1. 创建 Skill 目录和 SKILL.md

```bash
mkdir -p src/registry/skills/my-new-skill/scripts
```

```bash
cat > src/registry/skills/my-new-skill/SKILL.md << 'EOF'
---
name: my-new-skill
description: 我的新技能描述
execution:
  type: script
  handler: scripts/run.py
  entrypoint: main
  timeout: 30
---

技能说明文档...
EOF
```

### 2. 创建脚本

```python
cat > src/registry/skills/my-new-skill/scripts/run.py << 'EOF'
def main(**kwargs):
    return {"result": "Hello from my new skill!"}
EOF
```

### 3. 重启应用

所有 agent 将自动发现并可以使用新 skill。

## 可用 Skills

| Skill | 描述 | 类型 |
|-------|------|------|
| `semantic-search` | 向量语义搜索 | script |
| `tool-matcher` | 统计工具匹配 | script |
| `pipeline-decision` | 分析流程决策 | script |
| `question-generator` | 研究问题生成 | script |
| `literature-matcher` | 文献匹配 | script |
| `data-analyzer` | 数据分析 | script |
| `weather-query` | 实时天气查询 | script |

## 可用 Agents

| Agent | 描述 | Skills |
|-------|------|--------|
| `routing-agent` | 主控路由，分析意图并分发 | 自动发现所有 skills |
| `general-purpose-agent` | 通用问答、研究任务 | 自动发现所有 skills |
| `pipeline-agent` | 统计分析流程生成 | 自动发现所有 skills |
| `data-analyst-agent` | 数据分析、代码生成 | 自动发现所有 skills |

## 环境变量

### LLM 配置（通用，支持任意 OpenAI 兼容接口）

- `LLM_KEY`: LLM API Key（兼容旧名称 `QWEN_KEY`）
- `LLM_URL`: LLM API URL（兼容旧名称 `QWEN_URL`）
- `LLM_MODEL`: 模型名称（默认：gpt-3.5-turbo）
- `EMBEDDING_MODEL`: Embedding 模型（默认：text-embedding-ada-002）

### 服务配置

- `FLASK_HOST`: Flask 服务地址（默认：0.0.0.0）
- `FLASK_PORT`: Flask 服务端口（默认：8000）
- `DEBUG_MODE`: 调试模式开关（默认：false）

### 数据库配置

- `VECTOR_DB_PATH`: 向量数据库存储路径

### 外部 API

- `AMAP_KEY`: 高德地图 API Key（天气查询功能）

### 配置示例

```bash
# 使用通义千问
LLM_KEY=sk-xxx
LLM_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL=qwen-plus

# 使用 OpenAI
LLM_KEY=sk-xxx
LLM_URL=https://api.openai.com/v1
LLM_MODEL=gpt-3.5-turbo

# 使用其他兼容接口
LLM_KEY=your-key
LLM_URL=https://your-api-endpoint/v1
LLM_MODEL=your-model-name
```
