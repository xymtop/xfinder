#!/bin/bash

# xfinder 安装脚本
echo "正在安装 xfinder..."

# 检查是否安装了 uv
if ! command -v uv &> /dev/null; then
    echo "错误: 未找到 uv 工具，请先安装 uv"
    echo "安装方法: pip install uv"
    exit 1
fi

# 安装依赖
echo "安装依赖包..."
uv add pyyaml click colorama python-dotenv flet

# 安装 xfinder
echo "安装 xfinder..."
uv pip install -e .

echo "xfinder 安装完成！"
echo "使用方法:"
echo "  1. 启动图形界面: uv run xfinder app"
echo "  2. 一次性查询: uv run xfinder search "查询内容""
echo "  3. 查看帮助: uv run xfinder --help"
echo ""
echo "或者使用虚拟环境中的命令:"
echo "  1. 启动图形界面: .venv/bin/xfinder app"
echo "  2. 一次性查询: .venv/bin/xfinder search "查询内容""
echo "  3. 查看帮助: .venv/bin/xfinder --help"
