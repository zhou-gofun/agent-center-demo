#!/usr/bin/env python3
"""PDF 处理工具统一入口 - 通过 subprocess 调用各脚本"""

import argparse
import os
import subprocess
import sys


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def run_script(script_name, args):
    """调用指定脚本"""
    script_path = os.path.join(SCRIPT_DIR, script_name)
    cmd = ["python3", script_path] + args
    result = subprocess.run(cmd)
    sys.exit(result.returncode)


def main():
    parser = argparse.ArgumentParser(description="PDF 处理工具集")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # check-fillable-fields
    p1 = subparsers.add_parser("check-fillable-fields", help="检查 PDF 是否有可填充表单字段")
    p1.add_argument("input", help="输入 PDF 文件路径")

    # convert-to-images
    p2 = subparsers.add_parser("convert-to-images", help="将 PDF 转换为图片")
    p2.add_argument("input", help="输入 PDF 文件路径")
    p2.add_argument("output_dir", help="输出目录")
    p2.add_argument("--max-dim", type=int, default=1000, help="最大宽/高（默认 1000）")

    # check-bounding-boxes
    p3 = subparsers.add_parser("check-bounding-boxes", help="检查表单字段边界框")
    p3.add_argument("input", help="输入 PDF 文件路径")

    # fill-fillable-fields
    p4 = subparsers.add_parser("fill-fillable-fields", help="填充可填表单字段")
    p4.add_argument("input", help="输入 PDF 文件路径")
    p4.add_argument("output", help="输出 PDF 文件路径")
    p4.add_argument("data", help="填充数据（JSON 格式）")

    # fill-with-annotations
    p5 = subparsers.add_parser("fill-with-annotations", help="通过注解方式填充表单")
    p5.add_argument("input", help="输入 PDF 文件路径")
    p5.add_argument("output", help="输出 PDF 文件路径")
    p5.add_argument("data", help="填充数据（JSON 格式）")

    # extract-form-field-info
    p6 = subparsers.add_parser("extract-form-field-info", help="提取表单字段信息")
    p6.add_argument("input", help="输入 PDF 文件路径")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    if args.command == "check-fillable-fields":
        run_script("check_fillable_fields.py", [args.input])

    elif args.command == "convert-to-images":
        run_script("convert_pdf_to_images.py", [args.input, args.output_dir])

    elif args.command == "check-bounding-boxes":
        run_script("check_bounding_boxes.py", [args.input])

    elif args.command == "fill-fillable-fields":
        run_script("fill_fillable_fields.py", [args.input, args.output, args.data])

    elif args.command == "fill-with-annotations":
        run_script("fill_pdf_form_with_annotations.py", [args.input, args.output, args.data])

    elif args.command == "extract-form-field-info":
        run_script("extract_form_field_info.py", [args.input])


if __name__ == "__main__":
    main()
