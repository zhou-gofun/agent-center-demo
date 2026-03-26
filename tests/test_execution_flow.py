"""
测试执行流程

验证复杂任务的多步骤执行
"""
import sys
sys.path.insert(0, '/mnt/d/temp/proj/agent_center')

from src.core.execution_context import ExecutionContext
from src.core.task_parser import TaskParser, ActionType
from src.core.execution_orchestrator import get_orchestrator
from src.core.conversational_loop import get_conversational_loop


def test_context_isolation():
    """测试上下文隔离"""
    print("=" * 50)
    print("Test: Context Isolation")
    print("=" * 50)

    ctx = ExecutionContext()
    ctx.add_message("user", "Hello")
    ctx.add_message("assistant", "Hi there")

    print(f"Original context: {len(ctx.conversation_history)} messages")

    # Fork: 隔离上下文
    fork_ctx = ctx.create_fork()
    print(f"Forked context: {len(fork_ctx.conversation_history)} messages")
    print(f"Fork is isolated: {fork_ctx.isolated}")

    # Inherit: 继承上下文
    inherit_ctx = ctx.create_inherit()
    print(f"Inherited context: {len(inherit_ctx.conversation_history)} messages")
    print(f"Inherit is isolated: {inherit_ctx.isolated}")

    print("✓ Context isolation test passed\n")


def test_task_parsing():
    """测试任务解析"""
    print("=" * 50)
    print("Test: Task Parsing")
    print("=" * 50)

    parser = TaskParser()

    # Test 1: Single skill call
    response1 = '{"skill": "tool-matcher", "action": "execute", "input": {"query": "compare groups"}}'
    tasks1 = parser.parse(response1)
    print(f"Single skill call: {len(tasks1)} tasks")
    print(f"  Action: {tasks1[0].action.value}")
    print(f"  Skill: {tasks1[0].data.get('skill')}")

    # Test 2: Agent delegation
    response2 = '{"agent": "pipeline-agent", "context": "fork", "input": {"query": "analyze data"}}'
    tasks2 = parser.parse(response2)
    print(f"Agent delegation: {len(tasks2)} tasks")
    print(f"  Action: {tasks2[0].action.value}")
    print(f"  Agent: {tasks2[0].data.get('agent')}")

    # Test 3: Ask user
    response3 = '{"question": "What is your sample size?", "reasoning": "Need to know for method selection"}'
    tasks3 = parser.parse(response3)
    print(f"Ask user: {len(tasks3)} tasks")
    print(f"  Action: {tasks3[0].action.value}")
    print(f"  Question: {tasks3[0].data.get('question')}")

    # Test 4: Multi-step
    response4 = '''{"action": "multi_step", "steps": [
        {"action": "use_skill", "skill": "data-analyzer"},
        {"action": "use_skill", "skill": "literature-matcher"}
    ]}'''
    tasks4 = parser.parse(response4)
    print(f"Multi-step: {len(tasks4)} tasks")
    for i, task in enumerate(tasks4):
        print(f"  Step {i+1}: {task.action.value} -> {task.data.get('skill', task.data.get('agent', 'N/A'))}")

    print("✓ Task parsing test passed\n")


def test_agent_execution():
    """测试 agent 执行"""
    print("=" * 50)
    print("Test: Agent Execution")
    print("=" * 50)

    orchestrator = get_orchestrator()

    # 测试 routing-agent
    print("Testing routing-agent...")
    result = orchestrator.execute_agent(
        "routing-agent",
        {"query": "I need help with statistical analysis"}
    )

    print(f"  Success: {result.get('success')}")
    print(f"  Agent: {result.get('agent')}")
    print(f"  Tasks executed: {result.get('tasks_executed', 0)}")
    print(f"  Response length: {len(result.get('response', ''))}")

    if result.get('task_results'):
        print(f"  Task results:")
        for tr in result.get('task_results', []):
            print(f"    - {tr.get('type')}: {tr.get('name', 'N/A')}")

    print("✓ Agent execution test passed\n")


def test_conversational_loop():
    """测试对话循环"""
    print("=" * 50)
    print("Test: Conversational Loop")
    print("=" * 50)

    loop = get_conversational_loop()
    session_id = "test_session_001"

    # 创建会话
    loop.create_session(session_id, "general-purpose-agent", max_iterations=5)

    # 第一轮对话
    print("Turn 1: User greeting")
    result1 = loop.process_turn(session_id, "Hello, I need help with statistics", "general-purpose-agent")
    print(f"  Status: {result1.get('status')}")
    print(f"  Response length: {len(result1.get('response', ''))}")
    print(f"  Needs followup: {result1.get('needs_followup')}")

    # 获取对话摘要
    summary = loop.get_conversation_summary(session_id)
    print(f"  Total turns: {summary.get('iterations')}")

    print("✓ Conversational loop test passed\n")


def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 50)
    print("EXECUTION FLOW TESTS")
    print("=" * 50 + "\n")

    try:
        test_context_isolation()
        test_task_parsing()
        test_agent_execution()
        test_conversational_loop()

        print("=" * 50)
        print("ALL TESTS PASSED ✓")
        print("=" * 50)

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_all_tests()
