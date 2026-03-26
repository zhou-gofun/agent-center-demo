"""
调试追踪模块

提供详细的流程追踪和调试输出
"""
import json
import time
from typing import Dict, Any, Optional
from functools import wraps
from src.utils.logger import get_logger

logger = get_logger(__name__)


class RequestTracer:
    """请求追踪器 - 记录完整的请求流程"""

    def __init__(self, request_id: str = None):
        self.request_id = request_id or f"req_{int(time.time() * 1000)}"
        self.steps = []
        self.start_time = time.time()

    def add_step(self, step_type: str, data: Dict[str, Any]):
        """添加追踪步骤"""
        step = {
            "step": step_type,
            "timestamp": time.time() - self.start_time,
            "data": data
        }
        self.steps.append(step)

        # 实时打印
        self._print_step(step)

    def _print_step(self, step: Dict[str, Any]):
        """打印步骤详情"""
        step_type = step["step"]
        elapsed = step["timestamp"]
        data = step["data"]

        print(f"\n{'='*60}")
        print(f"📍 [{step_type}] T+{elapsed:.3f}s")
        print(f"{'='*60}")

        if step_type == "REQUEST_RECEIVED":
            print(f"📥 请求: {data.get('query', 'N/A')[:100]}")
            print(f"📋 Context keys: {list(data.get('context', {}).keys())}")

        elif step_type == "ROUTING_DECISION":
            print(f"🔀 路由决策: {data.get('target', 'N/A')}")
            print(f"💭 Reasoning: {data.get('reasoning', 'N/A')}")

        elif step_type == "AGENT_EXECUTION":
            print(f"🤖 Agent: {data.get('agent', 'N/A')}")
            print(f"📝 Skills: {data.get('skills', [])}")

        elif step_type == "SKILL_EXECUTION":
            print(f"🔧 Skill: {data.get('skill', 'N/A')}")
            if "result" in data:
                result = data["result"]
                if isinstance(result, dict) and "matched_tools" in result:
                    print(f"🎯 Matched: {len(result.get('matched_tools', []))} tools")
                elif isinstance(result, dict) and "results" in result:
                    print(f"🔍 Results: {len(result.get('results', []))} items")

        elif step_type == "AGENT_RESPONSE":
            response = data.get('response', '')
            print(f"💬 Response preview: {response[:200]}...")

        elif step_type == "FINAL_RESPONSE":
            print(f"✅ Agent Used: {data.get('agent_used', 'N/A')}")
            print(f"⏱️  Total Time: {data.get('execution_time', 0):.3f}s")

    def get_summary(self) -> Dict[str, Any]:
        """获取追踪摘要"""
        return {
            "request_id": self.request_id,
            "total_time": time.time() - self.start_time,
            "steps_count": len(self.steps),
            "steps": self.steps
        }


# 全局追踪器存储
_tracers: Dict[str, RequestTracer] = {}


def get_tracer(request_id: str) -> RequestTracer:
    """获取或创建追踪器"""
    if request_id not in _tracers:
        _tracers[request_id] = RequestTracer(request_id)
    return _tracers[request_id]


def trace_request(func):
    """请求追踪装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        # 创建追踪器
        tracer = RequestTracer()
        _tracers[tracer.request_id] = tracer

        # 记录请求开始
        request_data = kwargs.get('request_json', {})
        tracer.add_step("REQUEST_RECEIVED", {
            "query": request_data.get('query', ''),
            "context": request_data.get('context', {})
        })

        try:
            result = func(*args, **kwargs, tracer=tracer)

            # 记录最终响应
            if isinstance(result, dict) and "data" in result:
                tracer.add_step("FINAL_RESPONSE", {
                    "agent_used": result["data"].get("agent_used"),
                    "execution_time": result["data"].get("execution_time")
                })

            return result

        except Exception as e:
            tracer.add_step("ERROR", {"error": str(e)})
            raise

    return wrapper


def log_skill_execution(skill_name: str, input_data: Dict, result: Any):
    """记录技能执行详情"""
    print(f"\n{'─'*40}")
    print(f"🔧 SKILL: {skill_name}")
    print(f"{'─'*40}")

    print(f"📥 Input:")
    if "query" in input_data:
        print(f"   query: {input_data['query'][:100]}")
    if "data_summary" in input_data:
        print(f"   data_summary: {input_data['data_summary'][:100]}")
    for key in input_data:
        if key not in ["query", "data_summary"]:
            value = str(input_data[key])[:100]
            print(f"   {key}: {value}")

    print(f"\n📤 Output:")
    if isinstance(result, dict):
        if "error" in result:
            print(f"   ❌ Error: {result['error']}")
        elif "matched_tools" in result:
            tools = result.get("matched_tools", [])
            print(f"   🎯 Found {len(tools)} tools")
            for tool in tools[:3]:
                print(f"      - {tool.get('toolname', 'N/A')} (score: {tool.get('relevance_score', 0):.2f})")
        elif "results" in result:
            results = result.get("results", [])
            print(f"   🔍 Found {len(results)} results")
            for r in results[:3]:
                score = r.get("score", r.get("relevance_score", 0))
                name = r.get("toolname", r.get("title", "N/A"))
                print(f"      - {name} (score: {score:.2f})")
        elif "questions" in result:
            questions = result.get("questions", [])
            print(f"   ❓ Generated {len(questions)} questions")
            for q in questions[:2]:
                print(f"      - {q.get('question', 'N/A')[:60]}")
        elif "decision" in result:
            print(f"   🚦 Decision: {result.get('decision')}")
            print(f"   💭 Reasoning: {result.get('reasoning', 'N/A')[:100]}")
        elif "sample_size" in result:
            print(f"   📊 Sample size: {result.get('sample_size')}")
            print(f"   📊 Variables: {result.get('n_variables')}")
            print(f"   📊 Study design: {result.get('study_design')}")
        else:
            # 打印前几个键
            for key in list(result.keys())[:5]:
                value = str(result[key])[:100]
                print(f"   {key}: {value}")
    else:
        print(f"   {str(result)[:200]}")

    print(f"{'─'*40}")


def log_agent_execution(agent_name: str, input_data: Dict, result: Any):
    """记录 agent 执行详情"""
    print(f"\n{'='*50}")
    print(f"🤖 AGENT: {agent_name}")
    print(f"{'='*50}")

    print(f"📥 Input:")
    for key, value in list(input_data.items())[:5]:
        value_str = str(value)[:150]
        print(f"   {key}: {value_str}")

    if hasattr(result, 'response'):
        response = result.response
        print(f"\n💬 Response ({len(response)} chars):")
        print(f"   {response[:500]}")

        if hasattr(result, 'tool_calls') and result.tool_calls:
            print(f"\n🔧 Tool Calls:")
            for tc in result.tool_calls:
                print(f"   - {tc.name}: {list(tc.arguments.keys())}")

    print(f"{'='*50}")


class DebugExecutor:
    """调试执行器 - 包装标准执行器，添加详细日志"""

    def __init__(self, base_executor):
        self.base_executor = base_executor

    def execute_agent(self, agent_name: str, input_data: Dict) -> Any:
        """执行 agent 并记录详细日志"""
        print(f"\n\n{'█'*60}")
        print(f"🚀 EXECUTING AGENT: {agent_name}")
        print(f"{'█'*60}")

        # 调用原始执行器
        result = self.base_executor.execute_agent(agent_name, input_data)

        # 记录执行结果
        log_agent_execution(agent_name, input_data, result)

        return result

    def execute_skill(self, skill_name: str, input_data: Dict) -> Any:
        """执行 skill 并记录详细日志"""
        print(f"\n🔧 EXECUTING SKILL: {skill_name}")

        # 调用原始执行器
        result = self.base_executor.execute_skill(skill_name, input_data)

        # 记录执行结果
        log_skill_execution(skill_name, input_data,
                          result.metadata if hasattr(result, 'metadata') else result.response)

        return result


def enable_debug_mode():
    """启用调试模式"""
    import logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='[%(asctime)s] %(name)s [%(levelname)s] %(message)s',
        handlers=[logging.StreamHandler()]
    )

    # 设置关键模块为 DEBUG 级别
    for module_name in ['src.core.executor', 'src.core.agent_manager',
                         'src.core.skill_manager', 'src.api.routes']:
        logging.getLogger(module_name).setLevel(logging.DEBUG)

    print("🐛 DEBUG MODE ENABLED")
