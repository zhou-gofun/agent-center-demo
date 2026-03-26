#!/usr/bin/env python3
"""
Agent Center 流式交互终端

实时显示所有中间步骤：搜索、思考、Agent调用等
"""
import sys
import json
import time
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

BASE_URL = "http://localhost:8000/v1"


class Colors:
    """终端颜色"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[93m'
    END = '\033[0m'


def print_colored(text: str, color: str = Colors.END):
    """打印带颜色的文本"""
    print(f"{color}{text}{Colors.END}")


def print_header(text: str):
    """打印标题"""
    print_colored(f"\n{'=' * 60}", Colors.CYAN)
    print_colored(f"  {text}", Colors.CYAN)
    print_colored('=' * 60, Colors.CYAN)


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
        # 显示搜索结果
        results = metadata.get('results', [])
        if results:
            for r in results[:2]:
                tool_name = r.get('metadata', {}).get('toolname', 'N/A')
                score = r.get('score', 0)
                print(f"   • {tool_name} (相关度: {score:.2f})")

    elif event_type == 'agent_call':
        agent = metadata.get('agent', 'unknown')
        print_colored(f"🤖 {content}", Colors.BLUE)
        print(f"   Agent: {agent}")

    elif event_type == 'response':
        print_colored(f"\n📋 结果:", Colors.GREEN)
        # 缩进显示响应
        lines = content.split('\n')
        for line in lines:
            print(f"   {line}")

    elif event_type == 'confirm':
        print_colored(f"\n⚠️  {content}", Colors.YELLOW)
        print_colored("   请输入 y 确认继续，n 取消:", Colors.YELLOW)

    elif event_type == 'waiting':
        print_colored(f"⏸️  {content}", Colors.YELLOW)

    elif event_type == 'end':
        print_colored(f"\n✓ {content}", Colors.GREEN)

    else:
        print(f"{event_type}: {content}")


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


def check_service():
    """检查服务状态"""
    result, status = api_request("/health")
    return status == 200


def stream_chat(query: str, context: dict = None, session_id: str = "default"):
    """流式聊天"""
    print_header("Agent Center 流式聊天")

    # 发送请求
    result, status = api_request("/chat/stream", {
        "query": query,
        "context": context or {},
        "session_id": session_id
    })

    if status != 200 or not result.get("success"):
        print_colored(f"✗ 请求失败: {result.get('error', 'Unknown error')}", Colors.RED)
        return

    # 显示事件流
    events = result.get("events", [])
    requires_confirmation = result.get("requires_confirmation", False)

    for event in events:
        print_event(event)
        time.sleep(0.3)  # 模拟流式效果

    # 如果需要确认
    if requires_confirmation:
        while True:
            choice = input("\n> ").strip().lower()
            if choice in ['y', 'yes', '是']:
                # 确认继续
                print_colored("⏳ 正在继续执行...", Colors.YELLOW)
                result, status = api_request("/chat/confirm", {
                    "session_id": session_id,
                    "confirmed": True
                })

                if status == 200 and result.get("success"):
                    for event in result.get("events", []):
                        print_event(event)
                        time.sleep(0.3)
                break

            elif choice in ['n', 'no', '否']:
                # 取消
                result, status = api_request("/chat/confirm", {
                    "session_id": session_id,
                    "confirmed": False
                })
                print_colored("✓ 已取消", Colors.GREEN)
                break

            else:
                print_colored("请输入 y 或 n", Colors.YELLOW)


def interactive_mode():
    """交互模式"""
    print_header("Agent Center 流式交互终端")
    print_colored("实时显示所有中间步骤", Colors.CYAN)
    print("")

    session_id = f"session_{int(time.time())}"
    context = {}

    print("提示:")
    print("  输入问题后，会看到完整的处理流程")
    print("  包括: 搜索知识库 → 思考 → 调用Agent → 输出结果")
    print("  流程组配前会询问确认")
    print("  输入 'quit' 退出\n")

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
                ctx_str = query[9:].strip()
                try:
                    context.update(json.loads(ctx_str))
                    print_colored(f"✓ 上下文已更新: {context}", Colors.GREEN)
                except:
                    print_colored("✗ 无效的 JSON", Colors.RED)
                continue

            if query == '/clear':
                context = {}
                print_colored("✓ 上下文已清空", Colors.GREEN)
                continue

            # 执行流式聊天
            stream_chat(query, context, session_id)

        except KeyboardInterrupt:
            print_colored("\n再见!", Colors.GREEN)
            break
        except Exception as e:
            print_colored(f"✗ 错误: {str(e)}", Colors.RED)


def main():
    """主函数"""
    print()
    print_colored("""
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║          Agent Center 流式交互终端                         ║
    ║          实时显示所有中间处理步骤                           ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    """, Colors.CYAN)

    # 检查服务
    print("检查服务连接...")
    if not check_service():
        print_colored("✗ 无法连接到服务!", Colors.RED)
        print("\n请先启动服务:")
        print("  .venv_new/bin/python -m src.main")
        return 1

    print_colored("✓ 服务连接正常", Colors.GREEN)
    print_colored(f"API 地址: {BASE_URL}", Colors.CYAN)

    # 交互模式
    interactive_mode()

    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
