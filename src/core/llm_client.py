"""
Qwen LLM 客户端

使用 OpenAI 兼容模式调用 Qwen API
"""
import asyncio
from typing import List, Dict, Any, Optional
from openai import OpenAI, AsyncOpenAI
from config import get_config


class QwenClient:
    """Qwen API 同步客户端"""

    def __init__(self, api_key: str = None, base_url: str = None):
        cfg = get_config().qwen
        self.client = OpenAI(
            api_key=api_key or cfg.api_key,
            base_url=base_url or cfg.base_url,
            timeout=cfg.timeout
        )
        self.model = cfg.model
        self.embedding_model = cfg.embedding_model

    def chat(
        self,
        messages: List[Dict[str, str]],
        model: str = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """
        聊天接口

        Args:
            messages: 消息列表 [{"role": "user", "content": "..."}]
            model: 模型名称，默认使用配置中的模型
            temperature: 温度参数
            max_tokens: 最大 token 数
            **kwargs: 其他参数

        Returns:
            模型响应文本
        """
        response = self.client.chat.completions.create(
            model=model or self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        return response.choices[0].message.content

    def get_embedding(self, text: str) -> List[float]:
        """
        获取文本 embedding

        Args:
            text: 输入文本

        Returns:
            embedding 向量
        """
        response = self.client.embeddings.create(
            model=self.embedding_model,
            input=text
        )
        return response.data[0].embedding

    def get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        批量获取 embeddings

        Args:
            texts: 文本列表

        Returns:
            embedding 向量列表
        """
        response = self.client.embeddings.create(
            model=self.embedding_model,
            input=texts
        )
        return [item.embedding for item in response.data]


class AsyncQwenClient:
    """Qwen API 异步客户端"""

    def __init__(self, api_key: str = None, base_url: str = None):
        cfg = get_config().qwen
        self.client = AsyncOpenAI(
            api_key=api_key or cfg.api_key,
            base_url=base_url or cfg.base_url,
            timeout=cfg.timeout
        )
        self.model = cfg.model
        self.embedding_model = cfg.embedding_model

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: str = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """异步聊天接口"""
        response = await self.client.chat.completions.create(
            model=model or self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        return response.choices[0].message.content

    async def get_embedding(self, text: str) -> List[float]:
        """异步获取文本 embedding"""
        response = await self.client.embeddings.create(
            model=self.embedding_model,
            input=text
        )
        return response.data[0].embedding

    async def get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """异步批量获取 embeddings"""
        response = await self.client.embeddings.create(
            model=self.embedding_model,
            input=texts
        )
        return [item.embedding for item in response.data]


def get_llm_client() -> QwenClient:
    """获取同步 LLM 客户端实例"""
    return QwenClient()


def get_async_llm_client() -> AsyncQwenClient:
    """获取异步 LLM 客户端实例"""
    return AsyncQwenClient()
