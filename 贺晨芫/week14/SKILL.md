---
name: douyin-keyword-scraper
description: This skill should be used when the user wants to collect 巨量算数 (Douyin / OceanEngine) keyword search-index time series without a browser — triggers include "采集巨量算数关键词指数", "抖音关键词搜索指数", "直连 API + AES 解密", "看后搜指数", or scheduling periodic keyword-index scraping to Excel. It provides a self-contained Python script that POSTs the OceanEngine trend API, decrypts the AES-encrypted response, and writes an incremental Excel file.
---

# 巨量算数关键词指数采集（直连 API + AES 解密）

## Overview

无浏览器采集巨量算数（抖音）关键词的历史搜索指数：直连 OceanEngine 后端接口，对响应中的 AES 密文（`data` 字段）解密，提取每个关键词逐日搜索指数，写入 Excel 并按「关键词 + 日期」增量去重。相比浏览器拦截方案（DrissionPage），纯 `requests` 直连更快、更适合定时任务 / 云端运行。

## When to use

- 用户要采集「巨量算数 / 抖音关键词搜索指数」「关键词热度对比」「历史趋势分析」。
- 用户明确要求「直连 API + AES 解密」「不依赖浏览器 / DrissionPage」的采集方案。
- 需要把关键词指数定时落库到 Excel（可重复运行、只补新数据）。

## Workflow

1. 确认依赖已装：`pip install requests pycryptodome openpyxl`。
2. 更新脚本顶部 `COOKIE`：浏览器登录 `https://trendinsight.oceanengine.com` → DevTools → Network → 任意 XHR → 复制完整 Cookie（必须含有效 `msToken`）。详细步骤见 `references/api_notes.md`。
3. 设置关键词（推荐用 txt，无需改代码）：在 **项目目录 `C:\Users\ASUS\WorkBuddy\抖音\keywords.txt`** 逐行填写关键词，`#` 开头为注释。若项目目录无此文件，则回退到 skill 根目录的 `keywords.txt`。**直接增删该 txt 即可增加或减少采集词**。
4. 试跑校验：`python scripts/fetch.py --verify`（单批试跑，打印解密结果；上线前必做）。
5. 正式采集：`python scripts/fetch.py`。
   - 窗口：默认回推 `HISTORY_DAYS` 天；`--start/--end YYYYMMDD` 或 `--days N` 指定；`--keywords 词1 词2` 临时覆盖 txt。
   - **增量（默认开启）**：只在已有数据后补「上次采集末日 +1 ~ 今天」的新日期，状态存 `output/state.json`，大幅减少重复请求与解密；`--full` 强制全量重采。
   - **加速**：`--concurrency N`（默认 1 串行最稳；>1 用线程池并发，首跑提速，但注意风控）。
   - **重试**：网络 / 5xx 瞬态错误自动指数退避重试（默认 3 次，`--retries N`）；风控页面（非 JSON）不重试，需更新 Cookie。
6. 结果固定写到 **项目目录 `C:\Users\ASUS\WorkBuddy\抖音\output\keyword_index.xlsx`**（列：关键词 / 日期 / 关键词搜索指数），`output/` 目录会自动创建；二次运行仅追加新行。同目录 `state.json` 记录每个关键词已采集到的最新日期，供增量补数使用（误判时可删除该文件或加 `--full` 重置）。

## Key files

- `scripts/fetch.py` — 单文件自包含采集脚本（X-Bogus 纯 Python 实现 + AES CBC/CFB 解密 + 增量 xlsx 写出 + `--verify`/`--keywords`/`--start`/`--end`/`--days`）。
- `references/api_notes.md` — 接口字段、Cookie 提取步骤、AES 参数来源与刷新、排错（风控 / 过期 / X-Bogus 失效）。

## Notes

- Cookie 会过期；失效时脚本输出明确中文报错，按 `references/api_notes.md` 更新顶部 `COOKIE` 即可。
- 仅用于学习 / 自用，遵守网站 ToS，控制请求频率（默认批次延迟 1.5s）。
- 分享脚本前提醒用户：Cookie 属敏感登录态，需替换或脱敏，勿外泄。
