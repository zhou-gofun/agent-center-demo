#!/usr/bin/env python3
"""
Agent Center 交互式测试脚本

简单易用的测试工具，不需要额外安装 requests
"""
import sys
import json
from pathlib import Path

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    import urllib.request
    import urllib.error
    HAS_URLOPEN = True
except ImportError:
    HAS_URLOPEN = False


# API 基础 URL
BASE_URL = "http://localhost:8000/v1"


def api_request(method: str, endpoint: str, data: dict = None):
    """发送 API 请求"""
    url = f"{BASE_URL}{endpoint}"
    headers = {"Content-Type": "application/json"}

    try:
        if method == "GET":
            req = urllib.request.Request(url, headers=headers, method="GET")
        else:
            body = json.dumps(data).encode() if data else None
            req = urllib.request.Request(url, data=body, headers=headers, method=method)

        with urllib.request.urlopen(req, timeout=30) as response:
            response_data = response.read().decode('utf-8')
            return json.loads(response_data), response.status

    except urllib.error.HTTPError as e:
        return json.loads(e.read().decode('utf-8')), e.code
    except urllib.error.URLError as e:
        return {"error": f"连接失败: {str(e)}"}, 0
    except Exception as e:
        return {"error": str(e)}, 0


def print_box(text: str, width: int = 60):
    """打印带框的文本"""
    print("\n" + "─" * width)
    print(f" {text}")
    print("─" * width)


def print_json(data: dict, indent: int = 2):
    """美化打印 JSON"""
    print(json.dumps(data, ensure_ascii=False, indent=indent))


def interactive_menu():
    """交互式菜单"""
    options = [
        ("1", "健康检查", lambda: api_request("GET", "/health")),
        ("2", "服务信息", lambda: api_request("GET", "/info")),
        ("3", "列出所有 Agents", lambda: api_request("GET", "/registry/agents")),
        ("4", "列出所有 Skills", lambda: api_request("GET", "/registry/skills")),
        ("5", "获取 Pipeline Agent 详情", lambda: api_request("GET", "/registry/agents/pipeline_agent")),
        ("6", "知识库搜索", knowledge_search),
        ("7", "列出知识库集合", lambda: api_request("GET", "/knowledge/collections")),
        ("8", "执行 Pipeline Agent", execute_pipeline),
        ("9", "执行 Routing Agent", execute_routing),
        ("10", "流程生成快捷接口", pipeline_generate),
    ]

    while True:
        print("\n" + "=" * 60)
        print("  Agent Center 交互式测试")
        print("=" * 60)
        print("\n请选择测试项目:")

        for code, name, _ in options:
            print(f"  {code}. {name}")

        print("  0. 退出")
        print("-" * 60)

        choice = input("\n请输入选项 (0-10): ").strip()

        if choice == "0":
            print("退出测试")
            break

        for code, name, func in options:
            if choice == code:
                print_box(f"测试: {name}")
                result, status = func()
                print(f"\n状态码: {status}")
                print("\n响应:")
                print_json(result)
                break
        else:
            print("无效选项，请重新选择")


def knowledge_search():
    """知识库搜索"""
    print("\n请输入搜索关键词:")
    query = input("查询> ").strip() or "生存分析"
    print(f"\n搜索: {query}")

    return api_request("POST", "/knowledge/search", {
        "query": query,
        "collection": "assembly_tools",
        "top_k": 5
    })


def execute_pipeline():
    """执行 Pipeline Agent"""
    print("\n请输入数据分析需求 (留空使用默认示例):")
    query = input("查询> ").strip()

    if not query:
        query = "我想分析高血压患者的心血管事件风险，需要使用哪些统计工具？"

    print(f"\n执行查询: {query}")

    return api_request("POST", "/agent/pipeline_agent/execute", {
        "input": {
            "summary": "队列研究数据，包含1000名患者的随访数据",
            "query": query
        }
    })


def execute_routing():
    """执行 Routing Agent"""
    print("\n请输入问题 (留空使用默认):")
    query = input("查询> ").strip()

    if not query:
        query = "我需要分析临床数据，找出合适的统计方法"

    print(f"\n执行查询: {query}")

    return api_request("POST", "/agent/routing_agent/execute", {
        "input": {"query": query}
    })


def pipeline_generate():
    """流程生成"""
    print("\n请输入分析需求 (留空使用默认):")
    query = input("查询> ").strip()

    if not query:
        query = "比较不同治疗方案的疗效差异"

    print(f"\n生成流程: {query}")

    return api_request("POST", "/pipeline/generate", {
        "summary": "回顾性队列研究，500例糖尿病患者",
        "query": query
    })


def run_all_tests():
    """运行所有测试"""
    tests = [
        ("健康检查", lambda: api_request("GET", "/health")),
        ("服务信息", lambda: api_request("GET", "/info")),
        ("列出 Agents", lambda: api_request("GET", "/registry/agents")),
        ("列出 Skills", lambda: api_request("GET", "/registry/skills")),
        ("知识库集合", lambda: api_request("GET", "/knowledge/collections")),
    ]

    print("\n" + "=" * 60)
    print("  运行所有基础测试")
    print("=" * 60)

    results = []
    for name, func in tests:
        print_box(f"测试: {name}")
        _, status = func()
        print(f"状态: {'✓ 通过' if status == 200 else '✗ 失败'} ({status})")
        results.append((name, status == 200))

    print("\n" + "=" * 60)
    print("  测试结果汇总")
    print("=" * 60)
    for name, passed in results:
        status = "✓" if passed else "✗"
        print(f"  {status} {name}")

    passed_count = sum(1 for _, p in results if p)
    print(f"\n总计: {passed_count}/{len(results)} 通过")


def main():
    """主函数"""
    if not HAS_URLOPEN:
        print("错误: 缺少必要的模块")
        return 1

    print("\n" + "=" * 60)
    print("  Agent Center 交互式测试工具")
    print("=" * 60)
    print(f"\nAPI 地址: {BASE_URL}")
    print("\n提示: 请确保服务正在运行")
    print("  启动命令: .venv_new/bin/python -m src.main")

    # 检查连接
    print("\n检查服务连接...")
    _, status = api_request("GET", "/health")

    if status == 0:
        print("\n✗ 无法连接到服务！")
        print("\n请先启动 Agent Center 服务:")
        print("  cd /mnt/d/temp/proj/agent_center")
        print("  .venv_new/bin/python -m src.main")
        return 1

    print("✓ 服务连接正常\n")

    # 选择模式
    print("请选择测试模式:")
    print("  1. 交互式菜单")
    print("  2. 自动运行所有基础测试")

    mode = input("\n请选择 (1/2, 默认1): ").strip() or "1"

    if mode == "2":
        run_all_tests()
    else:
        interactive_menu()

    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
