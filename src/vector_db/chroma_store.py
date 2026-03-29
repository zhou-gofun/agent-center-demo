"""
ChromaDB 向量存储

提供向量数据库的封装接口
"""
import chromadb
from chromadb.config import Settings
from pathlib import Path
from typing import List, Dict, Any, Optional
from config import get_config
from utils.logger import get_logger

logger = get_logger(__name__)


class ChromaVectorStore:
    """ChromaDB 向量存储"""

    def __init__(self, persist_dir: str = None):
        """
        初始化向量存储

        Args:
            persist_dir: 持久化目录
        """
        cfg = get_config().vector_db
        self.persist_dir = Path(persist_dir or cfg.persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)

        # 创建持久化客户端
        self.client = chromadb.PersistentClient(
            path=str(self.persist_dir),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )

        self.collections = {}
        self.embedding_functions = {}

        # 暂时禁用自动加载已存在的集合，避免ONNX模型下载
        # self._load_existing_collections()

        logger.info(f"ChromaDB initialized at {self.persist_dir}")

    def create_collection(
        self,
        name: str,
        embedding_function,
        metadata: Dict = None
    ) -> None:
        """
        创建集合

        Args:
            name: 集合名称
            embedding_function: embedding 函数
            metadata: 集合元数据
        """
        self.embedding_functions[name] = embedding_function
        self.collections[name] = self.client.get_or_create_collection(
            name=name,
            embedding_function=embedding_function,
            metadata=metadata or {}
        )
        logger.info(f"Collection '{name}' created/loaded")

    def _load_existing_collections(self) -> None:
        """加载已存在的集合"""
        from vector_db.embeddings import get_embedding_function
        try:
            existing = self.client.list_collections()
            for coll in existing:
                name = coll.name
                if name not in self.collections:
                    # 获取默认embedding函数
                    try:
                        emb_fn = get_embedding_function()
                        self.collections[name] = coll
                        self.embedding_functions[name] = emb_fn
                        logger.info(f"Loaded existing collection: {name}")
                    except Exception as e:
                        logger.warning(f"Failed to load embedding for collection {name}: {e}")
                        # 仍然加载集合，但不设置embedding函数
                        self.collections[name] = coll
        except Exception as e:
            logger.debug(f"Failed to load existing collections: {e}")

    def get_collection(self, name: str):
        """获取集合"""
        if name not in self.collections:
            logger.warning(f"Collection '{name}' not found")
            return None
        return self.collections[name]

    def add_documents(
        self,
        collection: str,
        documents: List[str],
        metadatas: List[Dict] = None,
        ids: List[str] = None
    ) -> None:
        """
        添加文档到集合

        Args:
            collection: 集合名称
            documents: 文档文本列表
            metadatas: 元数据列表
            ids: 文档 ID 列表
        """
        col = self.get_collection(collection)
        if not col:
            raise ValueError(f"Collection '{collection}' not found")

        # 生成默认 ID
        if ids is None:
            ids = [f"{collection}_{i}" for i in range(len(documents))]

        col.add(
            documents=documents,
            metadatas=metadatas or [{}] * len(documents),
            ids=ids
        )
        logger.info(f"Added {len(documents)} documents to '{collection}'")

    def search(
        self,
        collection: str,
        query: str,
        top_k: int = 10,
        where: Dict = None,
        where_document: Dict = None
    ) -> List[Dict]:
        """
        语义搜索

        Args:
            collection: 集合名称
            query: 查询文本
            top_k: 返回结果数量
            where: 元数据过滤条件
            where_document: 文档内容过滤条件

        Returns:
            搜索结果列表
        """
        col = self.get_collection(collection)
        if not col:
            raise ValueError(f"Collection '{collection}' not found")

        results = col.query(
            query_texts=[query],
            n_results=top_k,
            where=where,
            where_document=where_document
        )

        return self._format_results(results, collection)

    def _format_results(self, results: Dict, collection: str) -> List[Dict]:
        """格式化搜索结果"""
        formatted = []

        if not results or not results.get("ids"):
            return formatted

        ids = results["ids"][0]
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        for i, doc_id in enumerate(ids):
            item = {
                "id": doc_id,
                "collection": collection,
                "document": documents[i] if i < len(documents) else "",
                "metadata": metadatas[i] if i < len(metadatas) else {},
                "score": 1 - distances[i] if i < len(distances) else 0.0
            }
            formatted.append(item)

        return formatted

    def delete(
        self,
        collection: str,
        ids: List[str] = None,
        where: Dict = None
    ) -> None:
        """
        删除文档

        Args:
            collection: 集合名称
            ids: 文档 ID 列表
            where: 元数据过滤条件
        """
        col = self.get_collection(collection)
        if not col:
            raise ValueError(f"Collection '{collection}' not found")

        col.delete(ids=ids, where=where)
        logger.info(f"Deleted documents from '{collection}'")

    def update(
        self,
        collection: str,
        ids: List[str],
        documents: List[str] = None,
        metadatas: List[Dict] = None
    ) -> None:
        """
        更新文档

        Args:
            collection: 集合名称
            ids: 文档 ID 列表
            documents: 新文档文本
            metadatas: 新元数据
        """
        col = self.get_collection(collection)
        if not col:
            raise ValueError(f"Collection '{collection}' not found")

        col.update(
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )
        logger.info(f"Updated {len(ids)} documents in '{collection}'")

    def get(
        self,
        collection: str,
        ids: List[str] = None,
        where: Dict = None,
        limit: int = None
    ) -> List[Dict]:
        """
        获取文档

        Args:
            collection: 集合名称
            ids: 文档 ID 列表
            where: 元数据过滤条件
            limit: 返回数量限制

        Returns:
            文档列表
        """
        col = self.get_collection(collection)
        if not col:
            raise ValueError(f"Collection '{collection}' not found")

        results = col.get(
            ids=ids,
            where=where,
            limit=limit
        )

        formatted = []
        for i, doc_id in enumerate(results.get("ids", [])):
            item = {
                "id": doc_id,
                "document": results.get("documents", [])[i] if i < len(results.get("documents", [])) else "",
                "metadata": results.get("metadatas", [])[i] if i < len(results.get("metadatas", [])) else {}
            }
            formatted.append(item)

        return formatted

    def count(self, collection: str) -> int:
        """获取集合文档数量"""
        col = self.get_collection(collection)
        if not col:
            return 0
        return col.count()

    def delete_collection(self, collection: str) -> None:
        """删除集合"""
        if collection in self.collections:
            self.client.delete_collection(collection)
            del self.collections[collection]
            if collection in self.embedding_functions:
                del self.embedding_functions[collection]
            logger.info(f"Collection '{collection}' deleted")

    def list_collections(self) -> List[str]:
        """列出所有集合"""
        return [c.name for c in self.client.list_collections()]

    def reset(self) -> None:
        """重置数据库（删除所有数据）"""
        self.client.reset()
        self.collections = {}
        self.embedding_functions = {}
        logger.warning("Database reset - all data deleted")


def get_vector_store() -> ChromaVectorStore:
    """获取向量存储实例"""
    return ChromaVectorStore()
