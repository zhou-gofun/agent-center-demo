"""
配置管理模块

支持环境变量和默认配置
"""
import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


@dataclass
class QwenConfig:
    """LLM API 配置（兼容任意 OpenAI 兼容接口）"""
    # 支持新旧环境变量名称：LLM_KEY/LLM_URL 或 QWEN_KEY/QWEN_URL
    api_key: str = field(default_factory=lambda: os.getenv("LLM_KEY") or os.getenv("QWEN_KEY", "sk-xxx"))
    base_url: str = field(default_factory=lambda: os.getenv("LLM_URL") or os.getenv("QWEN_URL", "https://api.openai.com/v1"))
    model: str = field(default_factory=lambda: os.getenv("LLM_MODEL", "gpt-3.5-turbo"))
    embedding_model: str = field(default_factory=lambda: os.getenv("EMBEDDING_MODEL", "text-embedding-ada-002"))
    timeout: int = 120


@dataclass
class FlaskConfig:
    """Flask 服务配置"""
    host: str = field(default_factory=lambda: os.getenv("FLASK_HOST", "0.0.0.0"))
    port: int = field(default_factory=lambda: int(os.getenv("FLASK_PORT", "8000")))
    debug: bool = field(default_factory=lambda: os.getenv("FLASK_DEBUG", "false").lower() == "true")


@dataclass
class VectorDBConfig:
    """向量数据库配置"""
    persist_dir: str = field(default_factory=lambda: os.getenv("VECTOR_DB_PATH", "./data/vector_store"))
    collection_assembly: str = "assembly_tools"
    collection_literature: str = "literature"


@dataclass
class DataConfig:
    """数据文件配置"""
    assembly_kb_path: str = field(default_factory=lambda: os.getenv("ASSEMBLY_KB_PATH", "./data/组配知识库.xlsx"))
    literature_kb_path: str = field(default_factory=lambda: os.getenv("LITERATURE_KB_PATH", "./data/pmcids_list.get.methods.filter(1).xlsx"))


@dataclass
class APIConfig:
    """外部 API 配置"""
    # 高德地图 API Key（用于天气查询等功能）
    amap_key: str = field(default_factory=lambda: os.getenv("AMAP_KEY", ""))


@dataclass
class RegistryConfig:
    """注册表配置"""
    agents_dir: str = "./registry/agents"
    skills_dir: str = "./registry/skills"
    agents_config: str = "./config/agents.yaml"
    skills_config: str = "./config/skills.yaml"


@dataclass
class Config:
    """总配置"""
    qwen: QwenConfig = field(default_factory=QwenConfig)
    flask: FlaskConfig = field(default_factory=FlaskConfig)
    vector_db: VectorDBConfig = field(default_factory=VectorDBConfig)
    data: DataConfig = field(default_factory=DataConfig)
    registry: RegistryConfig = field(default_factory=RegistryConfig)
    api: APIConfig = field(default_factory=APIConfig)

    # 项目根目录
    project_root: Path = field(default_factory=lambda: Path(__file__).parent.parent)
    src_dir: Path = field(default_factory=lambda: Path(__file__).parent)

    def __post_init__(self):
        """初始化路径为绝对路径"""
        if not isinstance(self.vector_db.persist_dir, Path):
            self.vector_db.persist_dir = str(self.project_root / self.vector_db.persist_dir)
        if not isinstance(self.data.assembly_kb_path, Path):
            self.data.assembly_kb_path = str(self.project_root / self.data.assembly_kb_path)
        if not isinstance(self.data.literature_kb_path, Path):
            self.data.literature_kb_path = str(self.project_root / self.data.literature_kb_path)
        if not isinstance(self.registry.agents_dir, Path):
            self.registry.agents_dir = str(self.src_dir / self.registry.agents_dir)
        if not isinstance(self.registry.skills_dir, Path):
            self.registry.skills_dir = str(self.src_dir / self.registry.skills_dir)
        if not isinstance(self.registry.agents_config, Path):
            self.registry.agents_config = str(self.project_root / self.registry.agents_config)
        if not isinstance(self.registry.skills_config, Path):
            self.registry.skills_config = str(self.project_root / self.registry.skills_config)


# 全局配置实例
config = Config()


def get_config() -> Config:
    """获取配置实例"""
    return config
