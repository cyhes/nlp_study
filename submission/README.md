# NLP Subagent Orchestrator

一个基于 **LangGraph** 的监督/编排 Agent：给定一段文本，由 *supervisor* 节点用
`Command` + `Send` API **并行派发**给多个 NLP 子代理（subagent），各自独立分析，最后由
*aggregator* 节点把结果汇总成一份 Markdown 报告。

```
        ┌─────────────┐
 text → │ supervisor  │ ──Send──▶ worker_classification ─┐
        └─────────────┘ ──Send──▶ worker_ner             │
                          ──Send──▶ worker_summarization  ├─▶ aggregator ──▶ report
                          ──Send──▶ worker_sentiment      │
                          ──Send──▶ worker_translation  ─┘
```

- 真并行：图通过 `ainvoke`（异步）+ 共享 `AsyncOpenAI` 客户端，`Send` 扇出的分支并发执行。
- 健壮性：每个 worker 内 `asyncio.wait_for` 超时 + `tenacity` 退避重试 + **失败隔离**
  （单个子代理出错只写入 `results`，不会拖垮其他分支或整张图）。
- 双形态：既提供 CLI，也暴露可 `import` 的库 API。
- 离线可用：无 API Key 时自动切换 `MockLLM`，端到端可跑、可测。

## 内置 NLP 角色

| 角色 | 说明 |
| --- | --- |
| `classification` | 文本分类（topic / intent 标签） |
| `ner` | 命名实体抽取（PER / ORG / LOC …） |
| `summarization` | 摘要 |
| `sentiment` | 情感分析（label / score） |
| `translation` | 翻译（→ 英文） |

## 安装（隔离 venv，不污染全局）

依赖安装到托管的 Python venv（`envs/default`）：

```bash
cd /c/Users/ASUS/WorkBuddy/NLP
ENV=/c/Users/ASUS/.workbuddy/binaries/python/envs/default
"$ENV/Scripts/python.exe" -m pip install -e ".[test]"
```

## 配置（环境变量 / `.env`）

复制 `.env.example` 为 `.env` 并按需修改：

| 变量 | 默认 | 说明 |
| --- | --- | --- |
| `DEEPSEEK_API_KEY` | — | DeepSeek key（无则自动走 Mock） |
| `MODEL_NAME` | `deepseek-chat` | 模型 id，例如 `deepseek-v4-flash` |
| `OPENAI_BASE_URL` | `https://api.deepseek.com` | OpenAI 兼容端点 |
| `NLP_TIMEOUT` | `30` | 每次调用的超时（秒） |
| `NLP_MAX_RETRIES` | `3` | 瞬时错误重试次数 |
| `NLP_MAX_BACKOFF` | `8` | 退避上限（秒） |
| `NLP_USE_MOCK` | — | 设为 `1` 强制离线 Mock |

DeepSeek 是 OpenAI 兼容端点，因此 `AsyncOpenAI(base_url=..., api_key=...)` 直接可用。

## 用法

### CLI

```bash
# 分析一段文本（默认跑全部角色）
"$ENV/Scripts/python.exe" -m orchestrator --text "Apple is buying a Beijing startup for $1B."

# 从文件读取，并写入报告
"$ENV/Scripts/python.exe" -m orchestrator --file input.txt --out report.md

# 只跑部分角色
"$ENV/Scripts/python.exe" -m orchestrator --text "..." --roles ner sentiment

# 离线演示（无需 key）
NLP_USE_MOCK=1 "$ENV/Scripts/python.exe" -m orchestrator --text "Hello world"
```

### 库 API

```python
from orchestrator import analyze_sync, analyze

# 同步
result = analyze_sync("Some text.")
print(result["final_report"])

# 只跑指定角色
result = analyze_sync("Some text.", roles=["ner", "sentiment"])

# 异步
result = await analyze("Some text.", roles=["classification"])

# 注入自定义 / Mock LLM
from orchestrator.llm import MockLLM
result = analyze_sync("text", llm=MockLLM())
```

返回值是完整的 `AgentState` 字典，关键字段：
- `results`: `{role: {"ok": bool, "data"|"error": ...}}`
- `final_report`: Markdown 报告字符串

## 扩展一个新角色

角色是 **数据** 而非拓扑。在 `src/orchestrator/roles/` 下新增一个模块并注册即可，图结构无需改动：

```python
# src/orchestrator/roles/keywords.py
import json
from .base import RoleDef, register

def parse_keywords(raw):
    return {"keywords": json.loads(raw).get("keywords", [])}

register(RoleDef(
    name="keywords",
    system="ROLE: keywords\nRespond ONLY with JSON {\"keywords\": [str]}.",
    build_user=lambda text: f"Extract keywords from:\n{text}",
    parse=parse_keywords,
))
```

然后在 `roles/__init__.py` 里 `from . import keywords`，新角色即刻出现在并行流水线中。

## 测试

```bash
"$ENV/Scripts/python.exe" -m pytest -q
```

测试用离线 `MockLLM` 验证：并行派发（耗时远小于串行）、结果聚合、以及**错误隔离**
（某一角色抛错不影响其他角色，aggregator 仍产出含成功与失败的报告）。

## 关键设计取舍

- **并行节点抛异常会自动取消兄弟分支并崩图** → worker 内部吞掉所有异常、把错误写进
  `results`，这是失败隔离的命门。
- **扇入靠拓扑**（`add_edge(worker_*, aggregator)`），不是共享 key；并发写 `results`
  必须配自定义 dict 合并 reducer，否则报 `INVALID_CONCURRENT_GRAPH_UPDATE`。
- **真并行只在 `ainvoke` 下发生**；CLI 通过 `asyncio.run(analyze(...))` 间接驱动。
