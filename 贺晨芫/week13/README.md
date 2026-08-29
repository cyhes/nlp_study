# Progressive Skill Harness

一套零依赖的 Python harness，用于**渐进式加载并执行** WorkBuddy 风格的 skills。

核心思想来自 skills 的 **三级渐进式披露（progressive disclosure）** 设计原则：

| 级别 | 内容 | 何时加载 | 内存代价 |
|------|------|----------|----------|
| **L1** | 元数据（name / description…） | 发现阶段，始终在内存 | 极低，只读 SKILL.md 头部 |
| **L2** | SKILL.md 正文 | 某个 skill 被选中 / 命中路由时 | 中等，按需 |
| **L3** | 打包资源（scripts / references / assets） | 执行阶段按需取用 | 仅用到的才加载 |

harness 的所有设计都围绕一个目标：**重内容只在真正需要时才进入内存**。

## 目录结构

```
skill-harness/
├── harness/
│   ├── __init__.py        # 公共导出
│   ├── frontmatter.py     # 极简 YAML frontmatter 解析 + 分词
│   ├── discovery.py       # L1 发现：扫描目录，构建轻量索引
│   ├── skill.py           # Skill 类：L2 懒加载正文、L3 懒加载/执行资源
│   ├── router.py          # 查询路由：打分选出最匹配的 skill
│   ├── loader.py          # ProgressiveLoader：编排 L1→L2→L3 状态机
│   ├── executor.py        # 执行器：DryRun / Script / Context 三种策略
│   └── cli.py             # 命令行入口
├── examples/
│   └── hello-skill/       # 最小可运行示例（SKILL.md + scripts + references）
└── tests/
    └── test_harness.py    # 自包含测试（无需 pytest）
```

## 安装 / 运行

零第三方依赖，标准库即可。推荐用托管 Python 3.13：

```bash
cd skill-harness
PYTHONPATH=. /path/to/python tests/test_harness.py      # 跑测试
PYTHONPATH=. /path/to/python -m harness.cli --help      # 看命令
```

> 注意：`--include-examples`、`--skills-dir`、`--workspace` 是**全局选项**，必须放在子命令之前。

## CLI 用法

```bash
# 列出所有发现的 skills（仅 L1 元数据）
python -m harness.cli list

# 用自然语言查询路由到候选 skill（中文按二元组分词，无需 embedding）
python -m harness.cli find "抖音 搜索指数"

# 加载某个 skill 正文（L2），并列出可用的 L3 资源
python -m harness.cli load douyin-keyword-scraper

# 预览执行计划（不真正运行）
python -m harness.cli --include-examples run hello-skill --dry

# 真正执行入口脚本（需显式 --yes 授权）
python -m harness.cli --include-examples run hello-skill --yes

# 组装 skill 上下文（L2 正文 + L3 references），交给 agent/LLM 处理
python -m harness.cli --include-examples context hello-skill
```

## 作为库使用

```python
from harness import SkillIndex, ProgressiveLoader, ContextExecutor

# L1：只读取每个 SKILL.md 的 frontmatter，快速建索引
index = SkillIndex.discover(["~/.workbuddy/skills", "examples/"])

# 路由
loader = ProgressiveLoader(index)
match = loader.select_best("演示 harness 测试")   # 返回 (Match, Skill)

# L2：此时只有命中 skill 的正文被加载
skill = loader.select("hello-skill")

# L3：按需加载 references / 执行 scripts
text = loader.load_reference(skill, "references/detail.md")
loader.run_script(skill, approve=True)

# 或者交给 agent：组装 body + references 作为上下文
ctx = ContextExecutor(load_references=True).execute(skill)
```

## 关键设计点

- **`SkillIndex.discover` 只读文件头**（默认前 80 行），因此即使有成百上千个 skill，建索引也很便宜——这就是 L1 的"渐进"。
- **`Skill.load_body()` 单例懒加载**——只有被选中的 skill 才会解析完整正文。
- **资源（scripts/references/assets）按目录扫描 + 按需读取/执行**，从不在发现阶段一次性读入。
- **`ProgressiveLoader` 记录每个 skill 当前级别**（1/2/3），便于观测和证明渐进行为。
- **执行器可插拔**：`DryRunExecutor`（安全、无副作用）、`ScriptExecutor`（真正跑入口脚本，需授权）、`ContextExecutor`（把 skill 上下文交给上层 agent）。
- **路由打分透明无依赖**：query 覆盖率 + 名称命中 + 短语包含，中文走二元组分词。

## 与现有 skills 的兼容性

直接扫描 `~/.workbuddy/skills`（user）与 `<workspace>/.workbuddy/skills`（project）。

入口脚本解析对真实 skill 的不规范布局很宽容，依次尝试：

1. frontmatter 的 `entry:` 字段
2. 正文里引用的 `.py` 路径（如 bash 块中的 `scraper.py`）
3. skill 根目录下的首选脚本名（`scraper.py` / `main.py` / `run.py` / `entry.py`）
4. skill 根目录下的任意脚本
5. `scripts/` 目录下的首选 / 首个脚本

解释器（`.py` 用哪个 python）解析顺序：frontmatter `interpreter:` →
正文里引用的 python 路径（如 `C:/Program Files/Python312/python.exe`）→
托管 `sys.executable`。

### 已接入：douyin-keyword-scraper

该真实技能脚本 `scraper.py` 位于 skill 根目录（非 `scripts/`），且依赖系统
Python 3.12。已在 `SKILL.md` frontmatter 显式补充：

```yaml
entry: scraper.py
interpreter: "C:/Program Files/Python312/python.exe"
```

接入后可直接：

```bash
python -m harness.cli find "抖音 搜索指数"      # 路由命中 douyin-keyword-scraper
python -m harness.cli run douyin-keyword-scraper --dry   # 预览执行计划
python -m harness.cli run douyin-keyword-scraper --yes   # 真正执行（需 DrissionPage + 有效 Cookie）
```

> 真实执行需要 `DrissionPage` / `pycryptodome` / `openpyxl` 与目标浏览器，
> 且 `scraper.py` 中的 Cookie 需有效；缺依赖或 Cookie 过期会由脚本本身报错。

