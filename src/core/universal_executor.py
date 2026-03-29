"""
通用脚本执行器

执行 skill 脚本，无需 Python 模块导入
支持：
1. 直接执行 .py 脚本文件
2. 动态调用指定入口函数
3. JSON 输入/输出
4. 超时控制
"""
import subprocess
import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from utils.logger import get_logger

logger = get_logger(__name__)


class UniversalScriptExecutor:
    """
    通用脚本执行器

    不依赖 importlib，通过以下方式执行：
    1. subprocess 隔离执行（默认）
    2. exec() 本地执行（可选，用于调试）
    """

    def __init__(self, timeout: int = 30, use_subprocess: bool = True):
        """
        初始化

        Args:
            timeout: 执行超时时间（秒）
            use_subprocess: 是否使用 subprocess（True）还是 exec()
        """
        self.timeout = timeout
        self.use_subprocess = use_subprocess

    def execute_skill(
        self,
        skill_name: str,
        skill_dir: Path,
        execution_config: Dict,
        input_data: Dict
    ) -> Optional[Dict]:
        """
        执行 skill 脚本

        Args:
            skill_name: skill 名称
            skill_dir: skill 目录路径
            execution_config: 执行配置
            input_data: 输入数据

        Returns:
            执行结果
        """
        exec_type = execution_config.get("type", "llm")

        if exec_type != "script":
            return {"error": f"Unsupported execution type: {exec_type}"}

        handler = execution_config.get("handler", "scripts/main.py")
        entrypoint = execution_config.get("entrypoint", "main")
        timeout = execution_config.get("timeout", self.timeout)

        script_path = skill_dir / handler

        if not script_path.exists():
            return {"error": f"Script not found: {script_path}"}

        print(f"\n{'─'*40}")
        print(f"🔧 EXECUTING SKILL: {skill_name}")
        print(f"{'─'*40}")
        print(f"📥 Script: {script_path}")
        print(f"📥 Handler: {handler}")
        print(f"📥 Entrypoint: {entrypoint}")
        print(f"📥 Input: {list(input_data.keys())}")

        # 执行脚本
        if self.use_subprocess:
            result = self._execute_with_subprocess(
                script_path, entrypoint, input_data, timeout
            )
        else:
            result = self._execute_with_exec(
                script_path, entrypoint, input_data
            )

        self._print_result_summary(result)

        print(f"{'─'*40}")

        return result

    def _execute_with_subprocess(
        self,
        script_path: Path,
        entrypoint: str,
        input_data: Dict,
        timeout: int
    ) -> Dict:
        """
        使用 subprocess 执行脚本

        通过 stdin 传递 JSON 输入，stdout 读取 JSON 输出
        """
        try:
            # 准备输入数据（包含入口点信息）
            exec_input = {
                "__entrypoint__": entrypoint,
                "__input__": input_data
            }
            input_json = json.dumps(exec_input, ensure_ascii=False)

            # 执行脚本
            result = subprocess.run(
                [sys.executable, str(script_path)],
                input=input_json,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(script_path.parent)
            )

            # 解析输出
            if result.returncode == 0:
                try:
                    output_data = json.loads(result.stdout)
                    return output_data
                except json.JSONDecodeError:
                    # 脚本返回非 JSON，直接返回文本
                    return {"result": result.stdout}
            else:
                error_msg = result.stderr or result.stdout
                return {"error": error_msg}

        except subprocess.TimeoutExpired:
            return {"error": f"Execution timeout after {timeout}s"}
        except Exception as e:
            logger.error(f"Error executing script {script_path}: {e}")
            return {"error": str(e)}

    def _execute_with_exec(
        self,
        script_path: Path,
        entrypoint: str,
        input_data: Dict
    ) -> Dict:
        """
        使用 exec() 执行脚本（用于调试）

        读取脚本内容，在当前进程中执行
        """
        try:
            # 读取脚本内容
            script_content = script_path.read_text(encoding='utf-8')

            # 准备执行环境
            exec_globals = {
                "__name__": "__skill__",
                "__file__": str(script_path),
                "__input__": input_data,
                "__result__": None
            }

            # 执行脚本
            exec(script_content, exec_globals)

            # 调用入口函数
            if entrypoint in exec_globals:
                func = exec_globals[entrypoint]
                if callable(func):
                    result = func(**input_data)
                    return result if isinstance(result, dict) else {"result": result}
                else:
                    return {"error": f"Entrypoint '{entrypoint}' is not callable"}
            else:
                return {"error": f"Entrypoint '{entrypoint}' not found in script"}

        except Exception as e:
            logger.error(f"Error executing script {script_path}: {e}")
            return {"error": str(e)}

    def _print_result_summary(self, result: Dict):
        """打印结果摘要"""
        if not result:
            print(f"✗ No result returned")
            return

        if "error" in result:
            print(f"✗ Error: {result['error']}")
            return

        if "matched_tools" in result:
            print(f"📤 Output: {len(result.get('matched_tools', []))} matched tools")
            for tool in result.get('matched_tools', [])[:3]:
                print(f"      - {tool.get('toolname', 'N/A')} (score: {tool.get('relevance_score', 0):.2f})")
        elif "results" in result:
            print(f"📤 Output: {len(result.get('results', []))} search results")
            for r in result.get('results', [])[:3]:
                score = r.get('score', 0)
                name = r.get('toolname', r.get('title', 'N/A'))
                print(f"      - {name} (score: {score:.2f})")
        elif "sample_size" in result:
            print(f"📤 Output: sample_size={result.get('sample_size')}, n_variables={result.get('n_variables')}")
        elif "decision" in result:
            print(f"📤 Output: decision={result.get('decision')}, confidence={result.get('confidence', 0):.2f}")
        elif "questions" in result:
            print(f"📤 Output: {len(result.get('questions', []))} questions generated")
        elif "response" in result:
            response = result['response']
            if len(response) > 100:
                print(f"📤 Output: {response[:100]}...")
            else:
                print(f"📤 Output: {response}")
        else:
            keys = list(result.keys())[:5]
            print(f"📤 Output: {keys}")


# 全局实例
_executor = None


def get_universal_executor() -> UniversalScriptExecutor:
    """获取执行器实例"""
    global _executor
    if _executor is None:
        _executor = UniversalScriptExecutor()
    return _executor
