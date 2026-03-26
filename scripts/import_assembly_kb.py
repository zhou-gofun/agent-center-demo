#!/usr/bin/env python3
"""
导入组配知识库到向量数据库
"""
import sys
import os
import pandas as pd
from pathlib import Path

# 添加项目根目录到路径
script_path = Path(__file__).resolve()
project_root = script_path.parent.parent
sys.path.insert(0, str(project_root))
os.chdir(project_root)

from src.vector_db.chroma_store import get_vector_store
from src.vector_db.embeddings import get_embedding_function


def import_assembly_knowledge():
    """导入组配知识库到 ChromaDB"""
    print("开始导入组配知识库...")

    # 读取 Excel
    excel_path = project_root / "data" / "组配知识库.xlsx"
    df = pd.read_excel(str(excel_path))

    print(f"读取了 {len(df)} 个工具")

    # 构建文档
    documents = []
    metadatas = []
    ids = []

    # 跟踪已使用的 toolid，处理重复
    used_toolids = {}

    for _, row in df.iterrows():
        # 构建文档文本 - 包含所有关键信息
        doc_text = f"""工具名称: {row['toolname']}
ID名称: {row['idname']}
工具ID: {row['toolid']}
描述: {row['description']}
应用场景: {row['applications']}
关键词: {row['keywords']}
使用条件: {row['conditions']}
"""

        # 构建元数据
        toolid = int(row['toolid']) if pd.notna(row['toolid']) else 0

        # 处理重复的 toolid
        if toolid in used_toolids:
            used_toolids[toolid] += 1
            unique_id = f"tool_{toolid}_{used_toolids[toolid]}"
        else:
            used_toolids[toolid] = 1
            unique_id = f"tool_{toolid}"

        metadata = {
            "toolid": toolid,
            "toolname": str(row['toolname']),
            "idname": str(row['idname']),
            "keywords": str(row['keywords']) if pd.notna(row['keywords']) else "",
            "applications": str(row['applications']) if pd.notna(row['applications']) else "",
            "conditions": str(row['conditions']) if pd.notna(row['conditions']) else ""
        }

        documents.append(doc_text)
        metadatas.append(metadata)
        ids.append(unique_id)

    # 导入到 ChromaDB
    store = get_vector_store()

    collection_name = "assembly_tools"

    # 删除旧集合（如果存在）
    if collection_name in store.list_collections():
        store.delete_collection(collection_name)

    # 使用 Qwen embedding（避免等待 sentence-transformers 下载）
    embedding_fn = get_embedding_function(use_local=False)

    # 创建新集合
    store.create_collection(
        collection_name,
        embedding_fn,
        metadata={"description": "组配工具知识库"}
    )

    # 添加文档
    store.add_documents(
        collection=collection_name,
        documents=documents,
        metadatas=metadatas,
        ids=ids
    )

    print(f"✓ 成功导入 {len(documents)} 个工具到集合 '{collection_name}'")

    # 显示统计
    print("\n工具统计:")
    print(f"  总数: {len(df)}")
    print(f"  toolid 范围: {df['toolid'].min()} - {df['toolid'].max()}")
    print(f"  示例工具: {', '.join(df['toolname'].head(5).tolist())}")

    return True


if __name__ == "__main__":
    try:
        import_assembly_knowledge()
    except Exception as e:
        print(f"导入失败: {e}")
        import traceback
        traceback.print_exc()
