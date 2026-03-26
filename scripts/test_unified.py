#!/usr/bin/env python3
"""
统一聊天接口测试脚本

测试 /v1/chat 统一入口
"""
import sys
import json
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

BASE_URL = "http://localhost:8000/v1"


def print_section(title: str):
    """打印分节标题"""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print('=' * 60)


def api_request(endpoint: str, data: dict = None):
    """发送 API 请求"""
    url = f"{BASE_URL}{endpoint}"
    headers = {"Content-Type": "application/json"}

    try:
        if data:
            body = json.dumps(data).encode()
            req = Request(url, data=body, headers=headers, method="POST")
        else:
            req = Request(url, headers=headers, method="GET")

        with urlopen(req, timeout=120) as response:
            return json.loads(response.read().decode('utf-8')), 200

    except HTTPError as e:
        try:
            return json.loads(e.read().decode('utf-8')), e.code
        except:
            return {"error": f"HTTP Error: {e.code}"}, e.code
    except URLError as e:
        return {"error": f"连接失败: {str(e)}"}, 0
    except Exception as e:
        return {"error": str(e)}, 0


def test_unified_chat():
    """测试统一聊天接口"""
    print_section("统一聊天接口测试")

    # 测试用例
    test_cases = [
        {
            "name": "统计分析需求",
            "query": "我想分析高血压患者的心血管事件风险，需要使用哪些统计工具？",
            "context": {
                "summary": "队列研究数据，包含1000名患者的随访数据"
            }
        },
        {
            "name": "工具查询",
            "query": "Kaplan-Meier 生存分析适用于什么场景？",
            "context": {}
        },
        {
            "name": "简单问题",
            "query": "什么是队列研究？",
            "context": {}
        },
        {
            "name": "代码生成需求",
            "query": "帮我写一个Python脚本来做t检验",
            "context": {
                "data_file": "clinical_data.csv"
            }
        }
    ]

    results = []

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n测试 {i}: {test_case['name']}")
        print(f"问题: {test_case['query']}")
        if test_case['context']:
            print(f"上下文: {test_case['context']}")

        print("调用中...")

        result, status = api_request("/chat", {
            "query": test_case['query'],
            "context": test_case['context']
        })

        if status == 200 and result.get("success"):
            data = result.get("data", {})
            print(f"✓ 成功")
            print(f"  使用的 Agent: {data.get('agent_used')}")
            print(f"  执行时间: {data.get('execution_time')}s")
            print(f"  响应: {data.get('response', '')[:200]}...")
            results.append((test_case['name'], True))
        else:
            print(f"✗ 失败: {result.get('error', 'Unknown error')}")
            results.append((test_case['name'], False))

    # 打印汇总
    print_section("测试结果汇总")
    for name, passed in results:
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"  {status} - {name}")

    passed_count = sum(1 for _, p in results if p)
    print(f"\n总计: {passed_count}/{len(results)} 通过")


def interactive_mode():
    """交互模式"""
    print_section("统一聊天接口 - 交互模式")
    print("输入问题，系统自动路由到合适的 Agent")
    print("输入 'quit' 退出\n")

    context = {}

    while True:
        try:
            query = input("You> ").strip()

            if not query:
                continue

            if query.lower() in ['quit', 'exit', 'q']:
                print("退出")
                break

            if query.startswith('/context '):
                ctx_str = query[9:].strip()
                try:
                    context.update(json.loads(ctx_str))
                    print(f"✓ 上下文已更新: {context}")
                except:
                    print("✗ 无效的 JSON")
                continue

            if query == '/clear':
                context = {}
                print("✓ 上下文已清空")
                continue

            print("处理中...")

            result, status = api_request("/chat", {
                "query": query,
                "context": context
            })

            if status == 200 and result.get("success"):
                data = result.get("data", {})
                print(f"\nAgent [{data.get('agent_used')}] ({data.get('execution_time')}s):")
                print(f"{data.get('response', '')}")
            else:
                print(f"✗ 错误: {result.get('error', 'Unknown error')}")

        except KeyboardInterrupt:
            print("\n退出")
            break
        except Exception as e:
            print(f"✗ 错误: {str(e)}")


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("  Agent Center 统一聊天接口测试")
    print("=" * 60)
    print(f"\nAPI 地址: {BASE_URL}/chat")

    # 检查服务
    print("\n检查服务...")
    result, status = api_request("/health")

    if status != 200:
        print("✗ 无法连接到服务！")
        print("\n请先启动服务:")
        print("  .venv_new/bin/python -m src.main")
        return 1

    print("✓ 服务正常\n")

    print("选择模式:")
    print("  1. 自动测试")
    print("  2. 交互模式")

    choice = input("\n请选择 (1/2, 默认2): ").strip() or "2"

    if choice == "1":
        test_unified_chat()
    else:
        interactive_mode()

    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
