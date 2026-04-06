# XFinder - 本地文件搜索工具

## 项目概述

XFinder 是一个功能强大的本地文件搜索工具，提供图形用户界面，灵感来自 Everything。它能够快速扫描和索引本地文件，支持多种搜索方式，帮助用户快速找到需要的文件。

## 核心特性

### 图形用户界面
- 直观的界面设计，操作简单易用
- 实时搜索结果显示
- 支持文件类型和项目类型筛选
- 支持多列排序
- 响应式布局，适配不同屏幕尺寸

### 索引模式

| 模式 | 说明 | 示例查询 |
|------|------|----------|
| **文件信息索引** | 索引文件名、路径、扩展名、大小、修改时间等元数据 | `resume.pdf`、`*.log` |
| **文件内容索引** | 对文本类文件进行全文索引，支持关键词检索 | `"TODO fixme"`、`import pandas` |

### 搜索功能
- 实时搜索：输入关键词时实时显示结果
- 多条件筛选：支持按文件类型、文件/文件夹类型筛选
- 排序功能：支持按名称、大小、修改时间排序
- 快速打开：双击结果直接打开文件或文件夹

## 环境要求

- Python 3.10 或更高版本
- uv 工具（用于依赖管理）
- Flet 库（用于图形界面）

## 安装部署步骤

### 方法一：使用安装脚本

1. 克隆项目到本地
   ```bash
   git clone https://github.com/yourusername/xfinder.git
   cd xfinder
   ```

2. 运行安装脚本
   ```bash
   ./install.sh
   ```

### 方法二：手动安装

1. 克隆项目到本地
   ```bash
   git clone https://github.com/yourusername/xfinder.git
   cd xfinder
   ```

2. 安装依赖
   ```bash
   uv add pyyaml flet tqdm
   ```

3. 安装 XFinder
   ```bash
   uv pip install -e .
   ```

## 使用指南

### 1. 启动应用程序

运行以下命令启动 XFinder 图形界面：

```bash
xfinder app
```

### 2. 构建索引

- 首次启动时，应用程序会提示你点击"重新构建"按钮来构建索引
- 在扫描目录输入框中输入要扫描的目录路径
- 点击"重新构建"按钮开始构建索引
- 索引构建完成后，状态栏会显示构建结果

### 3. 搜索文件

- 在搜索输入框中输入关键词
- 搜索结果会实时显示在下方的表格中
- 可以使用文件类型下拉框筛选特定类型的文件
- 可以使用类型下拉框筛选文件或文件夹
- 点击列标题可以对结果进行排序

### 4. 打开文件

- 双击搜索结果中的文件或文件夹，即可打开

### 5. 搜索语法

- **基本搜索**：直接输入关键词，如 `resume`
- **文件类型搜索**：使用文件类型下拉框选择
- **文件/文件夹筛选**：使用类型下拉框选择

## 配置文件

配置文件路径：`~/.xfinder/config.yaml`

```yaml
scan_paths:
  - ~/Documents
  - ~/Projects
exclude_dirs:
  - .git
  - node_modules
  - __pycache__
content_index:
  enabled: false  # 默认关闭内容索引，可根据需要开启
  extensions: [.txt, .md, .py, .js, .ts, .go, .java, .json, .yaml]
  max_file_size: 5MB
```

## 测试说明

### 运行单元测试

```bash
# 安装测试依赖
uv add pytest

# 运行测试
python -m pytest tests/ -v
```

### 性能测试

- **索引构建速度**：10 万文件以内，首次全量索引 < 60 秒
- **搜索响应时间**：文件名搜索 < 100ms；内容搜索 < 500ms

## 常见问题解答

### Q: 索引构建速度很慢，怎么办？
A: 可以通过以下方式优化：
- 在配置文件中减少 `scan_paths` 的范围
- 增加 `exclude_dirs` 排除不需要扫描的目录
- 关闭 `content_index.enabled` 禁用内容索引
- 调整 `content_index.max_file_size` 减小全文索引的文件大小限制

### Q: 搜索结果不包含某些文件，怎么办？
A: 检查以下几点：
- 确认文件是否在 `scan_paths` 范围内
- 确认文件类型是否在 `content_index.extensions` 中（如果是内容搜索）
- 确认文件大小是否超过 `content_index.max_file_size`（如果是内容搜索）

### Q: 应用程序启动时提示索引不存在，怎么办？
A: 点击"重新构建"按钮来构建索引。

### Q: 如何更改扫描目录？
A: 在扫描目录输入框中输入新的目录路径，然后点击"重新构建"按钮。

## 技术栈

- **开发语言**：Python
- **文件信息索引**：SQLite
- **全文索引**：SQLite FTS5
- **GUI 框架**：Flet
- **配置解析**：PyYAML
- **并发处理**：多线程

## 项目结构

```
xfinder/
├── src/
│   └── xfinder/
│       ├── __init__.py
│       ├── app.py         # 图形用户界面
│       ├── config.py      # 配置管理
│       ├── indexer.py     # 索引构建
│       ├── main.py        # 命令行入口
│       ├── sdk.py         # SDK 接口
│       ├── searcher.py    # 搜索核心
│       └── resource/      # 资源文件
│           ├── logo.png   # 应用图标
│           └── logo.icns  # macOS 图标
├── tests/
│   ├── test_config.py    # 配置测试
│   └── test_searcher.py  # 搜索测试
├── install.sh            # 安装脚本
├── pack.sh               # 打包脚本
├── pyproject.toml        # 项目配置
└── README.md             # 项目说明
```

## 版本历史

- **v0.1.0**：初始版本，支持文件信息索引、全文索引和基本搜索功能
- **v0.2.0**：添加图形用户界面，支持实时搜索和多条件筛选

## 许可证

MIT License
