---
name: hello-skill
description: 演示型技能：向用户问好并打印运行环境信息。用于验证 harness 的渐进式加载与脚本执行。当被问到"演示"、"hello"、"测试 harness"、"跑个示例"时触发。
location: example
agent_created: true
entry: scripts/greet.py
---

# Hello Skill

一个最小可运行的演示技能，用于验证 harness 的三级渐进式加载与脚本执行。

## 使用方式

运行入口脚本 `scripts/greet.py`，它会输出问候语与基础环境信息。

## 进阶说明

更详细的实现说明见 `references/detail.md`（按需加载，属于 Level 3 资源）。
