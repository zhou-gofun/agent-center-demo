#!/usr/bin/env python3
"""
Agent Center API 测试脚本

测试各个 API 端点的功能
"""
import sys
import json
import requests
from pathlib import Path

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


# API 基础 URL
BASE_URL = "http://localhost:8000/v1"


def print_section(title: str):
    """打印分节标题"""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print('=' * 60)


def print_result(response: requests.Response):
    """打印响应结果"""
    print(f"状态码: {response.status_code}")
    try:
        data = response.json()
        print(f"响应: {json.dumps(data, ensure_ascii=False, indent=2)}")
    except:
        print(f"响应: {response.text}")


def test_health():
    """测试健康检查"""
    print_section("1. 健康检查")
    response = requests.get(f"{BASE_URL}/health")
    print_result(response)
    return response.status_code == 200


def test_service_info():
    """测试服务信息"""
    print_section("2. 服务信息")
    response = requests.get(f"{BASE_URL}/info")
    print_result(response)
    return response.status_code == 200


def test_list_agents():
    """测试列出所有 agents"""
    print_section("3. 列出所有 Agents")
    response = requests.get(f"{BASE_URL}/registry/agents")
    print_result(response)
    return response.status_code == 200


def test_list_skills():
    """测试列出所有 skills"""
    print_section("4. 列出所有 Skills")
    response = requests.get(f"{BASE_URL}/registry/skills")
    print_result(response)
    return response.status_code == 200


def test_get_agent(agent_name: str = "pipeline_agent"):
    """测试获取单个 agent 详情"""
    print_section(f"5. 获取 Agent 详情: {agent_name}")
    response = requests.get(f"{BASE_URL}/registry/agents/{agent_name}")
    print_result(response)
    return response.status_code == 200


def test_execute_pipeline_agent():
    """测试执行 pipeline agent"""
    print_section("6. 执行 Pipeline Agent")

    # 模拟一个简单的数据分析需求
    input_data = {
        "summary": "队列研究数据，包含1000名患者的随访数据",
        "query": "我想分析高血压患者的心血管事件风险，需要使用哪些统计工具？"
    }

    print(f"输入: {json.dumps(input_data, ensure_ascii=False, indent=2)}")

    response = requests.post(
        f"{BASE_URL}/agent/pipeline_agent/execute",
        json={"input": input_data},
        headers={"Content-Type": "application/json"}
    )
    print_result(response)
    return response.status_code == 200


def test_execute_routing_agent():
    """测试执行 routing agent"""
    print_section("7. 执行 Routing Agent")

    input_data = {
        "query": "我需要分析临床数据，找出合适的统计方法"
    }

    print(f"输入: {json.dumps(input_data, ensure_ascii=False, indent=2)}")

    response = requests.post(
        f"{BASE_URL}/agent/routing_agent/execute",
        json={"input": input_data},
        headers={"Content-Type": "application/json"}
    )
    print_result(response)
    return response.status_code == 200


def test_knowledge_search():
    """测试知识库搜索"""
    print_section("8. 知识库语义搜索")

    query = "生存分析 Kaplan-Meier"
    print(f"搜索查询: {query}")

    response = requests.post(
        f"{BASE_URL}/knowledge/search",
        json={
            "query": query,
            "collection": "assembly_tools",
            "top_k": 5
        },
        headers={"Content-Type": "application/json"}
    )
    print_result(response)
    return response.status_code == 200


def test_list_collections():
    """测试列出知识库集合"""
    print_section("9. 列出知识库集合")
    response = requests.get(f"{BASE_URL}/knowledge/collections")
    print_result(response)
    return response.status_code == 200


def test_pipeline_generate():
    """测试流程生成快捷接口"""
    print_section("10. 流程生成快捷接口")

    input_data = {
        "summary": "回顾性队列研究，500例糖尿病患者",
        "query": "比较不同治疗方案的疗效差异"
    }

    print(f"输入: {json.dumps(input_data, ensure_ascii=False, indent=2)}")

    response = requests.post(
        f"{BASE_URL}/pipeline/generate",
        json=input_data,
        headers={"Content-Type": "application/json"}
    )
    print_result(response)
    return response.status_code == 200


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("  Agent Center API 测试")
    print("=" * 60)
    print(f"\nAPI 地址: {BASE_URL}")
    print("提示: 请确保服务正在运行 (python -m src.main)")

    # 等待用户确认
    input("\n按 Enter 开始测试...")

    # 测试列表
    tests = [
        ("健康检查", test_health),
        ("服务信息", test_service_info),
        ("列出 Agents", test_list_agents),
        ("列出 Skills", test_list_skills),
        ("获取 Agent 详情", test_get_agent),
        ("执行 Pipeline Agent", test_execute_pipeline_agent),
        ("执行 Routing Agent", test_execute_routing_agent),
        ("知识库搜索", test_knowledge_search),
        ("列出知识库集合", test_list_collections),
        ("流程生成", test_pipeline_generate),
    ]

    results = []

    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, "✓ 通过" if success else "✗ 失败"))
        except requests.exceptions.ConnectionError:
            results.append((name, "✗ 连接失败 - 请确保服务正在运行"))
            print("\n错误: 无法连接到服务，请先启动服务:")
            print("  cd /mnt/d/temp/proj/agent_center")
            print("  .venv_new/bin/python -m src.main")
            break
        except Exception as e:
            results.append((name, f"✗ 错误: {str(e)}"))

    # 打印测试结果汇总
    print_section("测试结果汇总")
    for name, result in results:
        print(f"  {name}: {result}")

    passed = sum(1 for _, r in results if "✓" in r)
    total = len(results)
    print(f"\n总计: {passed}/{total} 通过")


if __name__ == "__main__":
    main()
