"""
Embedding 生成

提供文本向量化的接口
"""
from typing import List, Union
from pathlib import Path
from core.llm_client import QwenClient
from config import get_config
from utils.logger import get_logger

logger = get_logger(__name__)

# 全局变量，懒加载模型
_sentence_model = None


def get_sentence_model():
    """获取 sentence-transformers 模型（单例）"""
    global _sentence_model
    if _sentence_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            model_path = Path(__file__).parent.parent.parent / "data" / "all-MiniLM-L6-v2"
            if model_path.exists():
                logger.info(f"Loading local sentence-transformer model from {model_path}")
                _sentence_model = SentenceTransformer(str(model_path))
            else:
                logger.info("Loading sentence-transformer model from hub")
                _sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
        except ImportError:
            logger.warning("sentence-transformers not installed, falling back to Qwen embeddings")
            return None
    return _sentence_model


class LocalEmbeddingFunction:
    """
    使用本地 sentence-transformers 模型的 Embedding 函数

    兼容 ChromaDB 的 embedding 函数接口
    """

    def __init__(self):
        """初始化本地 embedding 函数"""
        self.model = get_sentence_model()
        self._name = "local_minilm"

    def name(self):  # ChromaDB 需要可调用的 name()
        """ChromaDB 需要的 name 方法"""
        return self._name

    def __call__(self, input: Union[str, List[str]]) -> List[List[float]]:
        """
        生成 embedding

        Args:
            input: 输入文本或文本列表

        Returns:
            embedding 向量列表
        """
        if self.model is None:
            raise RuntimeError("sentence-transformers model not available")

        if isinstance(input, str):
            input = [input]

        # 使用 sentence-transformers 编码
        embeddings = self.model.encode(input, convert_to_numpy=True)
        return embeddings.tolist()


class QwenEmbeddingFunction:
    """
    Qwen Embedding 函数

    兼容 ChromaDB 的 embedding 函数接口
    """

    def __init__(self, client: QwenClient = None):
        """
        初始化 embedding 函数

        Args:
            client: Qwen 客户端
        """
        self.client = client or QwenClient()
        self._dimension = None
        self._name = "default"  # 内部存储

    def name(self):  # ChromaDB 需要可调用的 name()
        """ChromaDB 需要的 name 方法"""
        return self._name

    # ChromaDB 需要这些方法
    def _embed_with_retries(self, input: List[str]) -> List[List[float]]:
        """内部方法：带重试的 embedding"""
        return self.client.get_embeddings_batch(input)

    def __call__(self, input: Union[str, List[str]]) -> List[List[float]]:
        """
        生成 embedding

        Args:
            input: 输入文本或文本列表

        Returns:
            embedding 向量列表
        """
        if isinstance(input, str):
            return [self.client.get_embedding(input)]
        return self._embed_with_retries(input if isinstance(input, list) else [input])

    @property
    def dimension(self) -> int:
        """获取 embedding 维度"""
        if self._dimension is None:
            # 通过调用一次获取维度
            result = self.client.get_embedding("test")
            self._dimension = len(result)
        return self._dimension


class CachedEmbeddingFunction:
    """
    带缓存的 Embedding 函数

    避免重复计算相同文本的 embedding
    """

    def __init__(self, base_function: QwenEmbeddingFunction = None):
        """
        初始化带缓存的 embedding 函数

        Args:
            base_function: 基础 embedding 函数
        """
        self.base_function = base_function or QwenEmbeddingFunction()
        self._cache = {}
        self._name = "default"  # 内部存储

    def name(self):  # ChromaDB 需要可调用的 name()
        """ChromaDB 需要的 name 方法"""
        return self._name

    def __call__(self, input: Union[str, List[str]]) -> List[List[float]]:
        """生成 embedding（带缓存）"""
        if isinstance(input, str):
            input = [input]

        results = []
        for text in input:
            if text not in self._cache:
                self._cache[text] = self.base_function([text])[0]
            results.append(self._cache[text])

        return results

    def clear_cache(self) -> None:
        """清空缓存"""
        self._cache = {}

    def cache_size(self) -> int:
        """获取缓存大小"""
        return len(self._cache)


def get_embedding_function(use_local: bool = False, cached: bool = True):
    """
    获取 embedding 函数

    Args:
        use_local: 是否使用本地 sentence-transformers 模型（默认False，避免下载等待）
        cached: 是否使用缓存（仅对 Qwen 有效）

    Returns:
        embedding 函数实例
    """
    if use_local:
        model = get_sentence_model()
        if model is not None:
            return LocalEmbeddingFunction()
        logger.warning("Local model not available, falling back to Qwen")

    base_function = QwenEmbeddingFunction()
    if cached:
        return CachedEmbeddingFunction(base_function)
    return base_function


def compute_similarity(embedding1: List[float], embedding2: List[float]) -> float:
    """
    计算两个 embedding 的余弦相似度

    Args:
        embedding1: 第一个向量
        embedding2: 第二个向量

    Returns:
        相似度分数 (0-1)
    """
    import numpy as np

    vec1 = np.array(embedding1)
    vec2 = np.array(embedding2)

    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)

    if norm1 == 0 or norm2 == 0:
        return 0.0

    return dot_product / (norm1 * norm2)
