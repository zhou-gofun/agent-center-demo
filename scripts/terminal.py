#!/usr/bin/env python3
"""
Agent Center 交互式终端

提供命令行界面与 Agent 进行交互
"""
import sys
import json
import readline
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

# API 配置
BASE_URL = "http://localhost:8000/v1"


class Colors:
    """终端颜色"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_colored(text: str, color: str = Colors.END):
    """打印带颜色的文本"""
    print(f"{color}{text}{Colors.END}")


def print_header(text: str):
    """打印标题"""
    print_colored(f"\n{'=' * 60}", Colors.CYAN)
    print_colored(f"  {text}", Colors.CYAN)
    print_colored('=' * 60, Colors.CYAN)


def print_success(text: str):
    """打印成功消息"""
    print_colored(f"✓ {text}", Colors.GREEN)


def print_error(text: str):
    """打印错误消息"""
    print_colored(f"✗ {text}", Colors.RED)


def print_info(text: str):
    """打印信息"""
    print_colored(f"ℹ {text}", Colors.BLUE)


def api_request(method: str, endpoint: str, data: dict = None):
    """发送 API 请求"""
    url = f"{BASE_URL}{endpoint}"
    headers = {"Content-Type": "application/json"}

    try:
        if method == "GET":
            req = Request(url, headers=headers, method="GET")
        else:
            body = json.dumps(data).encode() if data else None
            req = Request(url, data=body, headers=headers, method="POST")

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
    result, status = api_request("GET", "/health")
    return status == 200


def get_agents():
    """获取所有可用 agents"""
    result, status = api_request("GET", "/registry/agents")
    if status == 200 and result.get("success"):
        return result.get("data", [])
    return []


def execute_agent(agent_name: str, query: str, context: dict = None):
    """执行 agent（使用统一聊天接口）"""
    # 使用统一 /chat 接口，系统会自动路由
    input_data = {"query": query}
    if context:
        input_data["context"] = context

    result, status = api_request("POST", "/chat", input_data)
    return result, status


def knowledge_search(query: str, collection: str = "assembly_tools", top_k: int = 5):
    """知识库搜索"""
    result, status = api_request("POST", "/knowledge/search", {
        "query": query,
        "collection": collection,
        "top_k": top_k
    })
    return result, status


def chat_mode(agent_name: str = "auto"):
    """智能聊天模式 - 使用统一接口自动路由"""
    print_header("智能聊天模式")
    print_info("系统会自动将你的问题路由到最合适的 agent")
    print_info("输入 'quit' 或 'exit' 退出")
    print("")

    # 对话历史
    conversation_history = []
    # 会话上下文（数据摘要等静态信息）
    session_context = {}

    while True:
        try:
            user_input = input(f"\n{Colors.GREEN}You{Colors.END}> ").strip()

            if not user_input:
                continue

            if user_input.lower() in ['quit', 'exit', 'q']:
                print_info("退出聊天模式")
                break

            # 处理命令
            if user_input.startswith('/'):
                cmd, *args = user_input.split(maxsplit=1)
                if cmd == '/context':
                    if args:
                        try:
                            session_context.update(json.loads(args[0]))
                            print_info(f"更新会话上下文: {session_context}")
                        except:
                            print_error("无效的 JSON")
                    else:
                        print_info(f"当前会话上下文: {session_context}")
                        print_info(f"对话历史: {len(conversation_history)} 条消息")
                    continue
                elif cmd == '/clear':
                    conversation_history = []
                    session_context = {}
                    print_info("清空所有上下文和历史")
                    continue
                elif cmd == '/history':
                    print_header("对话历史")
                    for i, msg in enumerate(conversation_history[-5:]):
                        role = msg.get('role', 'unknown')
                        content = msg.get('content', '')[:100]
                        print(f"{i+1}. [{role}]: {content}...")
                    continue
                elif cmd == '/search':
                    query = args[0] if args else input("搜索关键词> ")
                    result, status = knowledge_search(query)
                    if status == 200 and result.get("success"):
                        print_header("搜索结果")
                        for item in result.get("data", [])[:3]:
                            print(f"\n• {item.get('metadata', {}).get('toolname', 'N/A')}")
                            print(f"  分数: {item.get('score', 0):.2f}")
                    else:
                        print_error("搜索失败")
                    continue
                elif cmd == '/help':
                    print("""
可用命令:
  /context <json> - 设置会话上下文（如数据摘要）
  /clear          - 清空所有上下文和历史
  /history        - 查看对话历史
  /search <query> - 知识库搜索
  /help           - 显示帮助
  quit/exit       - 退出聊天

示例:
  /context {"summary": "600行数据，包含血压心率等"}
  /history
""")
                    continue

            # 添加用户消息到历史
            conversation_history.append({
                "role": "user",
                "content": user_input
            })

            # 执行查询（使用统一接口，自动路由）
            # 传递对话历史和会话上下文
            request_context = {
                **session_context,
                "conversation_history": conversation_history
            }

            result, status = execute_agent("auto", user_input, request_context)

            if status == 200 and result.get("success"):
                data = result.get("data", {})
                response = data.get("response", "")
                actual_agent = data.get("agent_used", "unknown")
                exec_time = data.get("execution_time", 0)

                # 添加助手响应到历史
                conversation_history.append({
                    "role": "assistant",
                    "content": response,
                    "agent": actual_agent
                })

                print(f"\n{Colors.BLUE}[{actual_agent}]{Colors.END} ({exec_time}s)>")
                print_colored(response, Colors.CYAN)
            else:
                print_error(f"请求失败: {result.get('error', 'Unknown error')}")
                # 移除失败的用户消息
                conversation_history.pop()

        except KeyboardInterrupt:
            print_info("\n退出聊天模式")
            break
        except Exception as e:
            print_error(f"错误: {str(e)}")


def interactive_mode():
    """交互模式菜单"""
    agents = get_agents()

    while True:
        print_header("Agent Center 交互终端")
        print()

        print("可用模式:")
        print("  1. 智能聊天 - 自动路由到合适的 agent")
        print("  2. 知识库搜索")
        print("  3. 列出所有 Agents")
        print("  4. 列出所有 Skills")
        print("  0. 退出")
        print()

        choice = input(f"{Colors.YELLOW}选择{Colors.END}> ").strip()

        if choice == "0":
            print_info("再见!")
            break
        elif choice == "1":
            chat_mode()
        elif choice == "2":
            query = input("\n搜索关键词> ").strip()
            if query:
                result, status = knowledge_search(query)
                if status == 200 and result.get("success"):
                    print_header("搜索结果")
                    for item in result.get("data", []):
                        print(f"\n• {item.get('metadata', {}).get('toolname', 'N/A')}")
                        print(f"  分数: {item.get('score', 0):.2f}")
                        metadata = item.get('metadata', {})
                        if 'description' in metadata:
                            print(f"  描述: {metadata['description'][:100]}...")
                else:
                    print_error("搜索失败")
        elif choice == "3":
            agents = get_agents()
            print_header("可用 Agents")
            for agent in agents:
                print(f"\n• {agent.get('name')}")
                print(f"  描述: {agent.get('description', 'N/A')}")
        elif choice == "4":
            result, status = api_request("GET", "/registry/skills")
            if status == 200 and result.get("success"):
                print_header("可用 Skills")
                for skill in result.get("data", []):
                    print(f"\n• {skill.get('name')}")
                    print(f"  描述: {skill.get('description', 'N/A')}")
            else:
                print_error("获取失败")


def main():
    """主函数"""
    print()
    print_colored("""
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║              Agent Center 交互式终端                      ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    """, Colors.CYAN)

    # 检查服务
    print("检查服务连接...")
    if not check_service():
        print_error("无法连接到服务!")
        print("\n请先启动服务:")
        print("  .venv_new/bin/python -m src.main")
        return 1

    print_success("服务连接正常")
    print_info(f"API 地址: {BASE_URL}")

    # 显示可用 agents
    agents = get_agents()
    if agents:
        print_info(f"已加载 {len(agents)} 个 Agents")
        for agent in agents[:3]:
            print(f"  • {agent.get('name')}")

    # 检查命令行参数
    if len(sys.argv) > 1:
        if sys.argv[1] in ['--chat', '-c']:
            agent_name = sys.argv[2] if len(sys.argv) > 2 else "pipeline_agent"
            chat_mode(agent_name)
        else:
            print("用法: python terminal.py [--chat|-c [agent_name]]")
    else:
        interactive_mode()

    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
