"""
数据加载器

从 Excel 文件加载知识库数据
"""
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any, Optional
from config import get_config
from utils.logger import get_logger

logger = get_logger(__name__)


class AssemblyKnowledgeLoader:
    """组配知识库加载器"""

    def __init__(self, file_path: str = None):
        """
        初始化加载器

        Args:
            file_path: Excel 文件路径
        """
        cfg = get_config().data
        self.file_path = Path(file_path or cfg.assembly_kb_path)
        self.data = None

    def load(self) -> pd.DataFrame:
        """
        加载数据

        Returns:
            数据 DataFrame
        """
        if not self.file_path.exists():
            raise FileNotFoundError(f"Assembly knowledge base not found: {self.file_path}")

        self.data = pd.read_excel(self.file_path)
        logger.info(f"Loaded {len(self.data)} records from {self.file_path}")
        return self.data

    def to_documents(self) -> List[Dict[str, Any]]:
        """
        转换为文档格式

        Returns:
            文档列表，每个文档包含 text 和 metadata
        """
        if self.data is None:
            self.load()

        documents = []

        for _, row in self.data.iterrows():
            # 构建文档文本
            parts = []
            for col in self.data.columns:
                if pd.notna(row[col]):
                    parts.append(f"{col}: {row[col]}")

            doc_text = "\n".join(parts)

            # 构建元数据
            metadata = {}
            for col in self.data.columns:
                if pd.notna(row[col]):
                    metadata[col] = str(row[col])

            documents.append({
                "text": doc_text,
                "metadata": metadata,
                "id": f"tool_{metadata.get('toolid', hash(doc_text))}"
            })

        return documents

    def get_tool_by_id(self, tool_id: int) -> Optional[Dict]:
        """
        根据 tool ID 获取工具信息

        Args:
            tool_id: 工具 ID

        Returns:
            工具信息字典
        """
        if self.data is None:
            self.load()

        if 'toolid' not in self.data.columns:
            return None

        result = self.data[self.data['toolid'] == tool_id]
        if result.empty:
            return None

        row = result.iloc[0]
        return {col: row[col] for col in self.data.columns}

    def search_tools(self, keyword: str) -> List[Dict]:
        """
        搜索工具（关键词搜索）

        Args:
            keyword: 搜索关键词

        Returns:
            匹配的工具列表
        """
        if self.data is None:
            self.load()

        # 简单的关键词匹配
        mask = self.data.astype(str).apply(
            lambda row: keyword.lower() in ' '.join(row.values).lower(),
            axis=1
        )

        results = self.data[mask]
        return [row.to_dict() for _, row in results.iterrows()]

    def get_categories(self) -> List[str]:
        """获取工具分类列表"""
        if self.data is None:
            self.load()

        if 'category' in self.data.columns:
            return self.data['category'].unique().tolist()
        return []

    def get_stats(self) -> Dict[str, Any]:
        """获取数据统计信息"""
        if self.data is None:
            self.load()

        return {
            "total_tools": len(self.data),
            "columns": list(self.data.columns),
            "categories": self.get_categories(),
            "file_path": str(self.file_path)
        }


class LiteratureKnowledgeLoader:
    """文献知识库加载器"""

    def __init__(self, file_path: str = None):
        """
        初始化加载器

        Args:
            file_path: Excel 文件路径
        """
        cfg = get_config().data
        self.file_path = Path(file_path or cfg.literature_kb_path)
        self.data = None

    def load(self) -> pd.DataFrame:
        """
        加载数据

        Returns:
            数据 DataFrame
        """
        if not self.file_path.exists():
            logger.warning(f"Literature knowledge base not found: {self.file_path}")
            self.data = pd.DataFrame()
            return self.data

        self.data = pd.read_excel(self.file_path)
        logger.info(f"Loaded {len(self.data)} records from {self.file_path}")
        return self.data

    def to_documents(self) -> List[Dict[str, Any]]:
        """
        转换为文档格式

        Returns:
            文档列表
        """
        if self.data is None:
            self.load()

        if self.data.empty:
            return []

        documents = []

        for _, row in self.data.iterrows():
            # 构建文档文本
            parts = []
            for col in self.data.columns:
                if pd.notna(row[col]):
                    parts.append(f"{col}: {row[col]}")

            doc_text = "\n".join(parts)

            # 构建元数据
            metadata = {}
            for col in self.data.columns:
                if pd.notna(row[col]):
                    metadata[col] = str(row[col])

            documents.append({
                "text": doc_text,
                "metadata": metadata,
                "id": f"literature_{metadata.get('pmcid', hash(doc_text))}"
            })

        return documents

    def get_stats(self) -> Dict[str, Any]:
        """获取数据统计信息"""
        if self.data is None:
            self.load()

        return {
            "total_records": len(self.data),
            "columns": list(self.data.columns) if not self.data.empty else [],
            "file_path": str(self.file_path)
        }


def get_assembly_loader() -> AssemblyKnowledgeLoader:
    """获取组配知识库加载器实例"""
    return AssemblyKnowledgeLoader()


def get_literature_loader() -> LiteratureKnowledgeLoader:
    """获取文献知识库加载器实例"""
    return LiteratureKnowledgeLoader()
