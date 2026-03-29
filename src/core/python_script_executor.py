"""
Python 脚本执行器

在隔离环境中执行 Python 脚本
"""
import subprocess
import tempfile
import json
from pathlib import Path
from typing import Dict, Any, Optional
from utils.logger import get_logger

logger = get_logger(__name__)


class PythonScriptExecutor:
    """
    Python 脚本执行器

    在隔离的子进程中执行 Python 脚本
    """

    def __init__(self, timeout: int = 30):
        """
        初始化

        Args:
            timeout: 执行超时时间（秒）
        """
        self.timeout = timeout

    def execute_skill_script(
        self,
        skill_name: str,
        script_path: Path,
        args: Dict[str, Any]
    ) -> Optional[Dict]:
        """
        执行 skill 的 Python 脚本

        Args:
            skill_name: skill 名称
            script_path: 脚本路径
            args: 输入参数

        Returns:
            执行结果（JSON 格式）
        """
        print(f"\n{'─'*40}")
        print(f"🔧 EXECUTING SKILL: {skill_name}")
        print(f"{'─'*40}")
        print(f"📥 Script: {script_path}")
        print(f"📥 Input: {list(args.keys())}")

        try:
            # 准备输入数据（通过标准输入传递 JSON）
            input_json = json.dumps(args, ensure_ascii=False)

            # 执行脚本
            result = subprocess.run(
                ["python", str(script_path)],
                input=input_json,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=str(script_path.parent)
            )

            # 解析输出
            if result.returncode == 0:
                try:
                    output_data = json.loads(result.stdout)

                    # 打印结果摘要
                    self._print_result_summary(skill_name, output_data)

                    print(f"{'─'*40}")
                    return output_data
                except json.JSONDecodeError:
                    # 脚本返回非 JSON，直接返回文本
                    output = {"result": result.stdout}
                    print(f"📤 Output: {result.stdout[:100]}...")
                    print(f"{'─'*40}")
                    return output
            else:
                error_msg = result.stderr or result.stdout
                print(f"✗ Error: {error_msg[:200]}")
                print(f"{'─'*40}")
                return {"error": error_msg}

        except subprocess.TimeoutExpired:
            print(f"✗ Timeout: Script execution exceeded {self.timeout}s")
            print(f"{'─'*40}")
            return {"error": f"Execution timeout after {self.timeout}s"}

        except Exception as e:
            print(f"✗ Exception: {e}")
            logger.error(f"Error executing skill script {skill_name}: {e}")
            print(f"{'─'*40}")
            return {"error": str(e)}

    def _print_result_summary(self, skill_name: str, result: Dict):
        """打印结果摘要"""
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
        else:
            keys = list(result.keys())[:5]
            print(f"📤 Output: {keys}")

    def execute_code_snippet(
        self,
        code: str,
        context: Dict[str, Any] = None
    ) -> Optional[Dict]:
        """
        执行代码片段（在临时文件中）

        Args:
            code: Python 代码
            context: 上下文变量

        Returns:
            执行结果
        """
        try:
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.py',
                delete=False
            ) as f:
                # 写入代码
                f.write(code)
                temp_path = Path(f.name)

            # 准备输入
            input_json = json.dumps(context or {}, ensure_ascii=False)

            # 执行
            result = subprocess.run(
                ["python", str(temp_path)],
                input=input_json,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )

            # 清理临时文件
            temp_path.unlink(missing_ok=True)

            if result.returncode == 0:
                try:
                    return json.loads(result.stdout)
                except json.JSONDecodeError:
                    return {"result": result.stdout}
            else:
                return {"error": result.stderr or result.stdout}

        except Exception as e:
            logger.error(f"Error executing code snippet: {e}")
            return {"error": str(e)}
