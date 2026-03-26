# Agent Center 测试脚本使用说明

## 脚本列表

### 1. 交互式测试 (推荐)
```bash
.venv_new/bin/python scripts/interactive_test.py
```

提供交互式菜单，可以选择不同的测试项目：
- 健康检查
- 服务信息
- 列出 Agents/Skills
- 知识库搜索
- 执行各种 Agent

### 2. 自动化测试
```bash
# 使用 Python (需要安装 requests)
.venv_new/bin/python scripts/test_api.py

# 使用 curl (无需额外依赖)
bash scripts/test.sh
```

自动运行所有测试用例并显示结果汇总。

### 3. 启动服务
```bash
# 使用启动脚本
bash scripts/run.sh

# 或直接运行
.venv_new/bin/python -m src.main
```

## 快速测试流程

1. **启动服务** (新终端窗口)
   ```bash
   cd /mnt/d/temp/proj/agent_center
   .venv_new/bin/python -m src.main
   ```

2. **运行测试** (另一个终端窗口)
   ```bash
   cd /mnt/d/temp/proj/agent_center
   .venv_new/bin/python scripts/interactive_test.py
   ```

## 测试 API 端点

### 健康检查
```bash
curl http://localhost:8000/v1/health
```

### 列出所有 Agents
```bash
curl http://localhost:8000/v1/registry/agents
```

### 执行 Pipeline Agent
```bash
curl -X POST http://localhost:8000/v1/agent/pipeline_agent/execute \
  -H "Content-Type: application/json" \
  -d '{"input": {"query": "如何进行生存分析？"}}'
```

### 知识库搜索
```bash
curl -X POST http://localhost:8000/v1/knowledge/search \
  -H "Content-Type: application/json" \
  -d '{"query": "Kaplan-Meier", "collection": "assembly_tools", "top_k": 5}'
```

## 预期输出

成功的测试应该显示：
- ✓ 服务连接正常
- ✓ 返回 Agent 列表
- ✓ 返回 Skill 列表
- ✓ Agent 执行返回分析结果
