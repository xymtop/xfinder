#!/bin/bash
# xfinder 打包脚本
# 支持 macOS、Windows、Linux 三平台打包
# 使用 PyInstaller + Flet 打包

set -e

APP_NAME="XFinder"
VERSION="0.1.0"
DIST_DIR="dist"

echo "========================================="
echo "  ${APP_NAME} v${VERSION} 打包脚本"
echo "========================================="

# 检查依赖
check_deps() {
    if ! command -v uv &> /dev/null; then
        echo "[错误] 未找到 uv，请先安装: https://docs.astral.sh/uv/"
        exit 1
    fi

    if ! uv run python -c "import flet" &> /dev/null; then
        echo "[提示] 正在使用 uv 同步依赖..."
        uv sync
    fi
}

# 清理旧的构建文件
clean() {
    echo "[清理] 清理旧的构建文件..."
    rm -rf build/ *.spec ${DIST_DIR}/
    echo "[清理] 完成"
}

# macOS 打包
pack_macos() {
    echo "========================================="
    echo "  macOS 打包"
    echo "========================================="

    # 使用 Flet 内置打包
    uv run flet pack src/xfinder/app.py \
        --name "${APP_NAME}" \
        --product-name "XFinder" \
        --bundle-id "com.xfinder" \
        --product-version "${VERSION}" \
        --distpath "${DIST_DIR}/macos" \
        --icon "src/xfinder/resource/logo.icns" \
        --add-data "src/xfinder:xfinder" \
        --add-data "pyproject.toml:." \
        --hidden-import xfinder \
        --hidden-import xfinder.app \
        --hidden-import xfinder.sdk \
        --hidden-import xfinder.indexer \
        --hidden-import xfinder.searcher \
        --hidden-import xfinder.config

    echo "[macOS] 打包完成: ${DIST_DIR}/macos/"
}

# Windows 打包
pack_windows() {
    echo "========================================="
    echo "  Windows 打包"
    echo "========================================="

    # 方式1: 使用 Flet 内置打包
    flet pack src/xfinder/app.py \
        --name "${APP_NAME}" \
        --product-name "xfinder" \
        --org "com.xfinder" \
        --version "${VERSION}" \
        --output-dir "${DIST_DIR}/windows" \
        --one-file

    # 方式2: 使用 PyInstaller (备选)
    # uv run pyinstaller --name "${APP_NAME}" \
    #     --onefile \
    #     --windowed \
    #     --add-data "src/xfinder;src/xfinder" \
    #     --add-data "pyproject.toml;." \
    #     --hidden-import xfinder \
    #     --hidden-import xfinder.app \
    #     --hidden-import xfinder.sdk \
    #     --hidden-import xfinder.indexer \
    #     --hidden-import xfinder.searcher \
    #     --hidden-import xfinder.config \
    #     src/xfinder/app.py

    echo "[Windows] 打包完成: ${DIST_DIR}/windows/"
}

# Linux 打包
pack_linux() {
    echo "========================================="
    echo "  Linux 打包"
    echo "========================================="

    # 方式1: 使用 Flet 内置打包
    flet pack src/xfinder/app.py \
        --name "${APP_NAME}" \
        --product-name "xfinder" \
        --org "com.xfinder" \
        --version "${VERSION}" \
        --output-dir "${DIST_DIR}/linux" \
        --one-file

    # 方式2: 使用 PyInstaller (备选)
    # uv run pyinstaller --name "${APP_NAME}" \
    #     --onefile \
    #     --windowed \
    #     --add-data "src/xfinder:src/xfinder" \
    #     --add-data "pyproject.toml:." \
    #     --hidden-import xfinder \
    #     --hidden-import xfinder.app \
    #     --hidden-import xfinder.sdk \
    #     --hidden-import xfinder.indexer \
    #     --hidden-import xfinder.searcher \
    #     --hidden-import xfinder.config \
    #     src/xfinder/app.py

    echo "[Linux] 打包完成: ${DIST_DIR}/linux/"
}

# 全部打包
pack_all() {
    clean
    check_deps

    echo "[安装] 使用 uv 同步依赖..."
    uv sync

    # 根据操作系统执行对应的打包命令
    OS=$(uname -s)
    case "${OS}" in
        Darwin)
            pack_macos
            ;;
        Linux)
            pack_linux
            ;;
        MINGW*|MSYS*|CYGWIN*)
            pack_windows
            ;;
        *)
            echo "[错误] 不支持的操作系统: ${OS}"
            exit 1
            ;;
    esac
}

# 显示帮助
show_help() {
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  all       打包当前平台 (默认)"
    echo "  macos     打包 macOS"
    echo "  windows   打包 Windows"
    echo "  linux     打包 Linux"
    echo "  clean     清理构建文件"
    echo "  help      显示此帮助"
    echo ""
    echo "示例:"
    echo "  ./pack.sh           # 打包当前平台"
    echo "  ./pack.sh macos     # 打包 macOS"
    echo "  ./pack.sh clean     # 清理构建文件"
}

# 主逻辑
case "${1:-all}" in
    all)
        pack_all
        ;;
    macos)
        clean
        check_deps
        uv sync
        pack_macos
        ;;
    windows)
        clean
        check_deps
        uv sync
        pack_windows
        ;;
    linux)
        clean
        check_deps
        uv sync
        pack_linux
        ;;
    clean)
        clean
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo "[错误] 未知选项: $1"
        show_help
        exit 1
        ;;
esac

echo ""
echo "========================================="
echo "  打包完成!"
echo "  输出目录: ${DIST_DIR}/"
echo "========================================="
