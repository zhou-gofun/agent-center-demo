#!/usr/bin/env python3
"""
Agent Center 流式交互终端（会话模式）

单个接口处理所有交互，包括确认
"""
import sys
import json
import time
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

BASE_URL = "http://localhost:8000/v1"


class Colors:
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    END = '\033[0m'


def print_colored(text: str, color: str = Colors.END):
    print(f"{color}{text}{Colors.END}")


def print_header(text: str):
    print_colored(f"\n{'=' * 60}", Colors.CYAN)
    print_colored(f"  {text}", Colors.CYAN)
    print_colored('=' * 60, Colors.CYAN)


def api_request(endpoint: str, data: dict = None):
    """发送 API 请求"""
    url = f"{BASE_URL}{endpoint}"
    headers = {"Content-Type": "application/json"}

    try:
        if data:
            body = json.dumps(data, ensure_ascii=False).encode('utf-8')
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


def print_event(event: dict):
    """打印事件"""
    event_type = event.get('type')
    content = event.get('content', '')
    metadata = event.get('metadata', {})

    if event_type == 'start':
        print_colored(f"\n▶ {content}", Colors.GREEN)

    elif event_type == 'thinking':
        print_colored(f"🤔 {content}", Colors.YELLOW)

    elif event_type == 'search':
        print_colored(f"🔍 {content}", Colors.CYAN)
        results = metadata.get('results', [])
        if results:
            for r in results[:2]:
                tool_name = r.get('metadata', {}).get('toolname', 'N/A')
                score = r.get('score', 0)
                print(f"   • {tool_name} (相关度: {score:.2f})")

    elif event_type == 'agent_call':
        agent = metadata.get('agent', 'unknown')
        print_colored(f"🤖 调用 {agent}...", Colors.BLUE)

    elif event_type == 'response':
        print_colored(f"\n📋 结果:", Colors.GREEN)
        # 显示前500字符
        preview = content[:500] + "..." if len(content) > 500 else content
        for line in preview.split('\n'):
            print(f"   {line}")

    elif event_type == 'confirm':
        print_colored(f"\n⚠️  {content}", Colors.YELLOW)

    elif event_type == 'end':
        print_colored(f"\n✓ {content}", Colors.GREEN)


def session_chat():
    """会话式聊天 - 所有交互通过统一接口"""
    print_header("Agent Center 流式交互终端")
    print_colored("实时显示: 搜索 → 思考 → 调用Agent → 输出", Colors.CYAN)
    print("")

    session_id = f"sess_{int(time.time())}"
    context = {}

    print("提示:")
    print("  - 流程组配前会自动询问确认")
    print("  - 输入 'quit' 退出\n")

    while True:
        try:
            query = input(f"{Colors.GREEN}You{Colors.END}> ").strip()

            if not query:
                continue

            if query.lower() in ['quit', 'exit', 'q']:
                print_colored("再见!", Colors.GREEN)
                break

            # 处理上下文命令
            if query.startswith('/context '):
                try:
                    context.update(json.loads(query[9:]))
                    print_colored(f"✓ 上下文已更新", Colors.GREEN)
                except:
                    print_colored("✗ 无效的 JSON", Colors.YELLOW)
                continue

            # 第一次请求 - 发送问题
            result, status = api_request("/chat/stream", {
                "query": query,
                "context": context,
                "session_id": session_id
            })

            if status != 200 or not result.get("success"):
                print_colored(f"✗ {result.get('error', '请求失败')}", Colors.YELLOW)
                continue

            # 显示事件流
            events = result.get("events", [])
            requires_confirmation = result.get("requires_confirmation", False)

            for event in events:
                print_event(event)
                time.sleep(0.2)

            # 如果需要确认，在当前会话中处理
            if requires_confirmation:
                while True:
                    choice = input(f"\n{Colors.YELLOW}确认继续? (y/n){Colors.END}> ").strip().lower()

                    if choice in ['y', 'yes', '是']:
                        # 确认 - 发送继续请求
                        print_colored("⏳ 继续执行...", Colors.YELLOW)

                        result, status = api_request("/chat/confirm", {
                            "session_id": session_id,
                            "confirmed": True
                        })

                        if status == 200 and result.get("success"):
                            for event in result.get("events", []):
                                print_event(event)
                                time.sleep(0.2)
                        break

                    elif choice in ['n', 'no', '否']:
                        # 取消
                        api_request("/chat/confirm", {
                            "session_id": session_id,
                            "confirmed": False
                        })
                        print_colored("✓ 已取消", Colors.GREEN)
                        break

                    else:
                        print_colored("请输入 y 或 n", Colors.YELLOW)

            # 如果已完成，重置会话
            if not requires_confirmation or any(e.get('type') == 'end' for e in events):
                session_id = f"sess_{int(time.time())}"

        except KeyboardInterrupt:
            print_colored("\n再见!", Colors.GREEN)
            break
        except Exception as e:
            print_colored(f"✗ 错误: {str(e)}", Colors.YELLOW)


def main():
    print()
    print_colored("""
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║          Agent Center 流式交互终端                         ║
    ║          实时显示处理流程 + 自动确认                        ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    """, Colors.CYAN)

    # 检查服务
    print("检查服务...")
    result, status = api_request("/health")
    if status != 200:
        print_colored("✗ 服务未运行", Colors.YELLOW)
        print("\n启动服务: .venv_new/bin/python -m src.main")
        return 1

    print_colored("✓ 服务正常", Colors.GREEN)

    session_chat()
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
