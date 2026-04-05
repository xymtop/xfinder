# xfinder - 命令行本地文件搜索工具

## 项目概述

xfinder 是一个命令行本地文件搜索工具，灵感来自 Everything，但专注于终端使用场景。用户运行工具后，系统自动构建索引，随后可通过命令行输入查询条件，快速返回搜索结果。

## 核心特性

### 启动时构建索引
- 程序启动时自动扫描指定目录（默认为用户主目录或配置的目标路径）
- 构建完成后提示用户，进入搜索就绪状态
- 索引持久化到本地，下次启动时重新构建（无需增量更新）

### 三种索引模式

| 模式 | 说明 | 示例查询 |
|------|------|----------|
| **文件信息索引** | 索引文件名、路径、扩展名、大小、修改时间等元数据 | `resume.pdf`、`*.log`、`size>10MB` |
| **文件内容索引** | 对文本类文件进行全文索引，支持关键词检索 | `"TODO fixme"`、`import pandas` |
| **大模型索引** | 用 LLM 对文件生成自然语言描述，支持语义搜索 | `上个月写的关于用户登录的代码`、`有没有处理支付的文件` |

### 命令行交互模式
- 支持两种使用方式：
  - **一次性查询**：`xfinder-search "查询内容"` 直接返回结果后退出
  - **交互模式**：`xfinder` 进入 REPL，可连续输入多条查询
- 输出格式为结构化列表，包含文件路径、匹配摘要、相关度分数

## 环境要求

- Python 3.10 或更高版本
- uv 工具（用于依赖管理）

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
   uv add pyyaml click colorama
   ```

3. 安装 xfinder
   ```bash
   uv pip install -e .
   ```

## 使用指南

### 1. 交互模式

运行 `xfinder` 命令进入交互模式，系统会自动构建索引，然后等待用户输入查询：

```bash
$ xfinder

正在构建索引...
  扫描文件信息: 82,341 个文件  ✓
  构建全文索引: 12,847 个文件  ✓
  语义索引: 已禁用（配置 llm_index.enabled=true 开启）

索引就绪，输入查询内容（Ctrl+C 退出）：

> resume

结果（共 3 条，耗时 12ms）：
  1. ~/Documents/resume_2024.pdf          [文件名匹配]
  2. ~/Projects/hr-system/models/resume.py [文件名匹配]
  3. ~/Notes/career/resume_tips.md         [内容匹配: "...更新你的 resume 时需要注意..."]

> "def authenticate" type:py

结果（共 2 条，耗时 45ms）：
  1. ~/Projects/api/auth.py:23             [内容匹配: "def authenticate(user, password):"]
  2. ~/Projects/legacy/login.py:87         [内容匹配: "def authenticate(token):"]
```

### 2. 一次性查询模式

使用 `xfinder-search` 命令进行一次性查询：

```bash
# 基本搜索
xfinder-search "resume"

# 带过滤条件
xfinder-search "type:py size>1KB"

# 输出 JSON 格式
xfinder-search --json "test"

# 限制返回条数
xfinder-search --limit 10 "config"

# 按名称排序
xfinder-search --sort name "test"
```

### 3. 搜索语法

- **文件名搜索**：直接输入关键词，如 `resume`、`*.pdf`
- **路径搜索**：输入路径片段，如 `Documents`、`Projects/api`
- **扩展名过滤**：`type:pdf`、`type:py`
- **大小过滤**：`size>1MB`、`size<100KB`
- **时间过滤**：`modified:7d`（最近7天）、`modified:2024-01`
- **全文搜索**：输入关键词，如 `import pandas`
- **短语搜索**：用引号包围，如 `"def authenticate"`

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
  enabled: true
  extensions: [.txt, .md, .py, .js, .ts, .go, .java, .json, .yaml]
  max_file_size: 5MB
llm_index:
  enabled: false
  base_url: "https://api.openai.com/v1"  # OpenAI 兼容的 API 地址
  api_key: ""
  model: "gpt-4o-mini"
  embedding_model: "text-embedding-3-small"
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
- **搜索响应时间**：文件名/内容搜索 < 200ms；语义搜索 < 2s（含网络）

## 常见问题解答

### Q: 索引构建速度很慢，怎么办？
A: 可以通过以下方式优化：
- 在配置文件中减少 `scan_paths` 的范围
- 增加 `exclude_dirs` 排除不需要扫描的目录
- 调整 `content_index.max_file_size` 减小全文索引的文件大小限制

### Q: 搜索结果不包含某些文件，怎么办？
A: 检查以下几点：
- 确认文件是否在 `scan_paths` 范围内
- 确认文件类型是否在 `content_index.extensions` 中（如果是内容搜索）
- 确认文件大小是否超过 `content_index.max_file_size`（如果是内容搜索）

### Q: 如何开启语义搜索功能？
A: 在配置文件中设置：
- `llm_index.enabled: true`
- 填写 `llm_index.api_key` 为你的 OpenAI API Key
- 可选：调整 `llm_index.model` 和 `llm_index.embedding_model`

### Q: 搜索语法有哪些？
A: 支持以下语法：
- 文件名/路径搜索：直接输入关键词
- 扩展名过滤：`type:pdf`
- 大小过滤：`size>1MB`
- 时间过滤：`modified:7d`
- 全文搜索：直接输入关键词
- 短语搜索：用引号包围，如 `"def authenticate"`

## 技术栈

- **开发语言**：Python
- **文件信息索引**：SQLite
- **全文索引**：SQLite FTS5
- **CLI 框架**：Click
- **配置解析**：PyYAML

## 项目结构

```
xfinder/
├── src/
│   └── xfinder/
│       ├── __init__.py
│       ├── config.py      # 配置管理
│       ├── indexer.py     # 索引构建
│       ├── searcher.py    # 搜索核心
│       └── main.py        # CLI 入口
├── tests/
│   ├── test_config.py    # 配置测试
│   └── test_searcher.py  # 搜索测试
├── install.sh            # 安装脚本
├── pyproject.toml        # 项目配置
└── README.md             # 项目说明
```

## 版本历史

- **v0.1.0**：初始版本，支持文件信息索引、全文索引和基本搜索功能

## 许可证

MIT License
