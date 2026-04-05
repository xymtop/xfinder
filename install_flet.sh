#!/bin/bash

# 使用虚拟环境中的python
VENV_PYTHON=/Users/xiaoyemiao/Desktop/xfinder/.venv/bin/python

# 获取Flet版本
FLET_VERSION=$($VENV_PYTHON -c "import flet_desktop.version; print(flet_desktop.version.version)")

# 创建Flet客户端缓存目录
FLET_CACHE_DIR=~/.flet/client/flet-desktop-full-$FLET_VERSION
mkdir -p "$FLET_CACHE_DIR"

# 解压Flet客户端
echo "正在解压 Flet v$FLET_VERSION..."
tar -xzf flet-macos.tar.gz -C "$FLET_CACHE_DIR"

# 检查安装是否成功
if [ -f "$FLET_CACHE_DIR/Flet.app/Contents/MacOS/Flet" ]; then
    echo "Flet客户端安装成功！"
    echo "安装路径: $FLET_CACHE_DIR"
else
    echo "Flet客户端安装失败，请检查解压过程。"
fi
