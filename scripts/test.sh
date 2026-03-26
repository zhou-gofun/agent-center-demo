#!/bin/bash
# Agent Center API 测试脚本 (使用 curl)

BASE_URL="http://localhost:8000/v1"

echo "=========================================="
echo "  Agent Center API 测试"
echo "=========================================="
echo "API 地址: $BASE_URL"
echo ""

# 检查服务是否运行
echo "检查服务状态..."
response=$(curl -s "$BASE_URL/health")
if [[ $? -ne 0 ]]; then
    echo "✗ 无法连接到服务！"
    echo ""
    echo "请先启动服务:"
    echo "  ./scripts/run.sh"
    echo "或:"
    echo "  .venv_new/bin/python -m src.main"
    exit 1
fi

echo "✓ 服务运行正常"
echo ""

# 1. 健康检查
echo "─────────────────────────────────────"
echo "1. 健康检查"
echo "─────────────────────────────────────"
curl -s "$BASE_URL/health" | python3 -m json.tool
echo ""

# 2. 服务信息
echo "─────────────────────────────────────"
echo "2. 服务信息"
echo "─────────────────────────────────────"
curl -s "$BASE_URL/info" | python3 -m json.tool
echo ""

# 3. 列出所有 Agents
echo "─────────────────────────────────────"
echo "3. 列出所有 Agents"
echo "─────────────────────────────────────"
curl -s "$BASE_URL/registry/agents" | python3 -m json.tool
echo ""

# 4. 列出所有 Skills
echo "─────────────────────────────────────"
echo "4. 列出所有 Skills"
echo "─────────────────────────────────────"
curl -s "$BASE_URL/registry/skills" | python3 -m json.tool
echo ""

# 5. 获取 Pipeline Agent 详情
echo "─────────────────────────────────────"
echo "5. 获取 Pipeline Agent 详情"
echo "─────────────────────────────────────"
curl -s "$BASE_URL/registry/agents/pipeline_agent" | python3 -m json.tool
echo ""

# 6. 列出知识库集合
echo "─────────────────────────────────────"
echo "6. 列出知识库集合"
echo "─────────────────────────────────────"
curl -s "$BASE_URL/knowledge/collections" | python3 -m json.tool
echo ""

# 7. 执行 Routing Agent
echo "─────────────────────────────────────"
echo "7. 执行 Routing Agent"
echo "─────────────────────────────────────"
curl -s -X POST "$BASE_URL/agent/routing_agent/execute" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "query": "我需要分析临床数据，找出合适的统计方法"
    }
  }' | python3 -m json.tool
echo ""

# 8. 执行 Pipeline Agent
echo "─────────────────────────────────────"
echo "8. 执行 Pipeline Agent (这可能需要一些时间...)"
echo "─────────────────────────────────────"
curl -s -X POST "$BASE_URL/agent/pipeline_agent/execute" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "summary": "队列研究数据，包含1000名患者的随访数据",
      "query": "我想分析高血压患者的心血管事件风险，需要使用哪些统计工具？"
    }
  }' | python3 -m json.tool
echo ""

echo "=========================================="
echo "  测试完成"
echo "=========================================="
