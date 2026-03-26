#!/usr/bin/env python3
"""
测试脚本 - 演示完整的请求流程

运行这个脚本来观察完整的消息流转和调试输出
"""
import sys
import requests
import json

# API 基础 URL
BASE_URL = "http://localhost:8000/v1"


def print_separator(title: str):
    """打印分隔符"""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")


def test_direct_query():
    """测试1: 直接查询"""
    print_separator("测试 1: 直接查询 - 如何做差异分析")

    response = requests.post(f"{BASE_URL}/chat", json={
        "query": "如何做差异分析，需要考虑哪些细节？"
    })

    result = response.json()
    print(f"状态: {result.get('success')}")
    print(f"使用的 Agent: {result.get('data', {}).get('agent_used')}")
    print(f"执行时间: {result.get('data', {}).get('execution_time')}s")

    # 打印响应的前500个字符
    resp_text = result.get('data', {}).get('response', '')
    print(f"\n响应预览:\n{resp_text[:500]}...")


def test_with_data_summary():
    """测试2: 带数据摘要的查询"""
    print_separator("测试 2: 带数据摘要 - 分析我的数据")

    data_summary = """
Skim summary statistics
 n obs: 150
 n variables: 8

Variable type: numeric
  min mean max sd
  age 18 45.2 89 15.3
  bmi 18.5 25.4 45.2 4.2

Variable type: categorical
  n_missing top_counts
  treatment 0 group A: 75, group B: 75
"""

    response = requests.post(f"{BASE_URL}/chat", json={
        "query": "帮我分析这组数据，应该用什么统计方法？",
        "context": {
            "data_summary": data_summary
        }
    })

    result = response.json()
    print(f"状态: {result.get('success')}")
    print(f"使用的 Agent: {result.get('data', {}).get('agent_used')}")

    # 打印调试信息
    debug_info = result.get('data', {}).get('debug', {})
    if debug_info:
        print(f"\n调试信息:")
        print(f"  调用的 Agents: {debug_info.get('agents_called', [])}")
        print(f"  搜索结果数: {debug_info.get('search_results_count', 0)}")
        print(f"  步骤: {[s['step'] for s in debug_info.get('steps', [])]}")

    print(f"\n响应预览:\n{result.get('data', {}).get('response', '')[:500]}...")


def test_pipeline_request():
    """测试3: 直接请求流程组配"""
    print_separator("测试 3: 直接请求流程组配")

    response = requests.post(f"{BASE_URL}/chat", json={
        "query": "请为我创建一个比较两组均值的t检验流程"
    })

    result = response.json()
    print(f"状态: {result.get('success')}")
    print(f"使用的 Agent: {result.get('data', {}).get('agent_used')}")

    print(f"\n响应预览:\n{result.get('data', {}).get('response', '')[:500]}...")


def check_debug_status():
    """检查调试状态"""
    print_separator("调试状态检查")

    response = requests.get(f"{BASE_URL}/debug/status")
    result = response.json()

    print(f"调试模式: {result.get('data', {}).get('debug_mode')}")
    print(f"日志级别: {result.get('data', {}).get('log_level')}")

    # 切换调试模式
    if not result.get('data', {}).get('debug_mode'):
        print("\n正在启用调试模式...")
        requests.post(f"{BASE_URL}/debug/toggle")
        print("✓ 调试模式已启用")


def show_system_info():
    """显示系统信息"""
    print_separator("系统信息")

    response = requests.get(f"{BASE_URL}/info")
    result = response.json()

    if result.get('success'):
        data = result.get('data', {})
        print(f"版本: {data.get('version')}")
        print(f"Agent 数量: {data.get('agents_count')}")
        print(f"Skill 数量: {data.get('skills_count')}")
        print(f"\n可用的 Agents:")
        for agent in data.get('agents', []):
            print(f"  - {agent}")
        print(f"\n可用的 Skills:")
        for skill in data.get('skills', []):
            print(f"  - {skill}")


def main():
    """主函数"""
    print("\n🚀 Agent Center 流程追踪测试\n")

    try:
        # 检查服务状态
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code != 200:
            print("❌ 服务未运行，请先启动服务:")
            print("   cd /mnt/d/temp/proj/agent_center && python src/main.py")
            return

        print("✓ 服务正在运行\n")

        # 显示系统信息
        show_system_info()

        # 检查并启用调试模式
        check_debug_status()

        input("\n按 Enter 开始测试...")

        # 运行测试
        test_direct_query()
        input("\n按 Enter 继续下一个测试...")

        test_with_data_summary()
        input("\n按 Enter 继续下一个测试...")

        test_pipeline_request()

        print_separator("测试完成")

    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到服务，请确保服务正在运行")
        print("   启动命令: cd /mnt/d/temp/proj/agent_center && python src/main.py")
    except Exception as e:
        print(f"❌ 错误: {e}")


if __name__ == "__main__":
    main()
