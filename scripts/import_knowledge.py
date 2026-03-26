"""
知识库数据导入脚本

将 Excel 数据导入到 ChromaDB 向量数据库
"""
import sys
from pathlib import Path

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.vector_db.chroma_store import get_vector_store
from src.vector_db.embeddings import get_embedding_function
from src.vector_db.data_loader import get_assembly_loader, get_literature_loader
from src.utils.logger import get_logger

logger = get_logger(__name__)


def import_assembly_knowledge():
    """导入组配知识库到 ChromaDB"""
    logger.info("开始导入组配知识库...")

    # 加载数据
    loader = get_assembly_loader()
    documents = loader.to_documents()

    logger.info(f"加载了 {len(documents)} 个工具文档")

    # 初始化向量存储
    store = get_vector_store()
    embedding_fn = get_embedding_function()

    # 创建集合
    collection_name = "assembly_tools"
    if collection_name not in store.list_collections():
        store.create_collection(collection_name, embedding_fn)

    # 清空现有数据
    try:
        store.delete_collection(collection_name)
        store.create_collection(collection_name, embedding_fn)
        logger.info(f"清空并重新创建集合: {collection_name}")
    except Exception as e:
        logger.warning(f"清空集合失败: {e}")

    # 批量添加文档
    texts = [doc["text"] for doc in documents]
    metadatas = [doc["metadata"] for doc in documents]
    ids = [doc["id"] for doc in documents]

    store.add_documents(collection_name, texts, metadatas, ids)

    logger.info(f"成功导入 {len(documents)} 个工具到集合 '{collection_name}'")

    # 显示统计信息
    stats = loader.get_stats()
    logger.info(f"数据统计: {stats}")


def import_literature_knowledge():
    """导入文献知识库到 ChromaDB"""
    logger.info("开始导入文献知识库...")

    # 加载数据
    loader = get_literature_loader()
    documents = loader.to_documents()

    if not documents:
        logger.warning("文献知识库为空")
        return

    logger.info(f"加载了 {len(documents)} 个文献文档")

    # 初始化向量存储
    store = get_vector_store()
    embedding_fn = get_embedding_function()

    # 创建集合
    collection_name = "literature"
    if collection_name not in store.list_collections():
        store.create_collection(collection_name, embedding_fn)

    # 批量添加文档
    texts = [doc["text"] for doc in documents]
    metadatas = [doc["metadata"] for doc in documents]
    ids = [doc["id"] for doc in documents]

    store.add_documents(collection_name, texts, metadatas, ids)

    logger.info(f"成功导入 {len(documents)} 个文献到集合 '{collection_name}'")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="导入知识库数据")
    parser.add_argument(
        "--type",
        choices=["assembly", "literature", "all"],
        default="all",
        help="要导入的知识库类型"
    )

    args = parser.parse_args()

    if args.type in ["assembly", "all"]:
        import_assembly_knowledge()

    if args.type in ["literature", "all"]:
        import_literature_knowledge()

    logger.info("导入完成")


if __name__ == "__main__":
    main()
