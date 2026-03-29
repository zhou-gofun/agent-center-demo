"""
Flask 应用入口

Agent 中心的主应用入口点
"""
import os
from flask import Flask, jsonify
from flask_cors import CORS
from config import get_config
from api.routes import api_bp
from utils.logger import get_logger
from core.agent_manager import AgentManager
from core.skill_manager import SkillManager
from core.registry_scanner import get_scanner

logger = get_logger(__name__)

# 全局扫描器实例
registry_scanner = None


def create_app(config=None) -> Flask:
    """
    创建 Flask 应用

    Args:
        config: 自定义配置

    Returns:
        Flask 应用实例
    """
    app = Flask(__name__)

    # 加载配置
    cfg = config or get_config()

    # 启用 CORS
    CORS(app, resources={
        r"/v1/*": {
            "origins": "*",
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
        }
    })

    # 注册蓝图
    app.register_blueprint(api_bp)

    # 根路径
    @app.route('/')
    def index():
        return jsonify({
            "name": "Agent Center",
            "version": "1.0.0",
            "description": "通用 Agent 中心服务",
            "unified_endpoint": {
                "path": "/v1/chat",
                "method": "POST",
                "description": "统一聊天接口 - 唯一对外入口，自动路由到合适的 agent"
            },
            "endpoints": {
                "chat": "/v1/chat",
                "agents": "/v1/registry/agents",
                "skills": "/v1/registry/skills",
                "execute": "/v1/agent/<name>/execute",
                "search": "/v1/knowledge/search",
                "pipeline": "/v1/pipeline/generate",
                "health": "/v1/health"
            }
        })

    # 错误处理
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            "success": False,
            "error": "Endpoint not found"
        }), 404

    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal error: {error}")
        return jsonify({
            "success": False,
            "error": "Internal server error"
        }), 500

    # 初始化组件
    _init_components()

    return app


def _init_components():
    """初始化核心组件"""
    global registry_scanner

    try:
        # 初始化 agent 和 skill 管理器
        agent_manager = AgentManager()
        skill_manager = SkillManager()

        # 动态扫描并注册 skills 和 agents
        registry_scanner = get_scanner()
        registry = registry_scanner.scan()

        logger.info(f"Discovered {len(registry['skills'])} skills from {registry_scanner.skills_dir}")
        logger.info(f"Discovered {len(registry['agents'])} agents from {registry_scanner.agents_dir}")

        # 从配置文件加载 agents 和 skills（已禁用 - 避免覆盖手动编辑的文件）
        # agent_manager.reload_from_config()
        # skill_manager.reload_from_config()

        logger.info(f"Loaded {len(agent_manager.list_agents())} agents")
        logger.info(f"Loaded {len(skill_manager.list_skills())} skills")

    except Exception as e:
        logger.warning(f"Failed to load initial agents/skills: {e}")


def main():
    """主函数"""
    cfg = get_config()

    app = create_app()

    logger.info(f"Starting Agent Center on {cfg.flask.host}:{cfg.flask.port}")

    app.run(
        host=cfg.flask.host,
        port=cfg.flask.port,
        debug=cfg.flask.debug
    )


if __name__ == '__main__':
    main()
