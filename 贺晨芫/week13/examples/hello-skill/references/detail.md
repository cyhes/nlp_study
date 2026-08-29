# Hello Skill 实现细节

- 入口脚本通过 `sys.argv` 接收可选的名字参数，缺省为 `"world"`。
- 该文件属于 `references/`，仅当 harness 进入 Level 3 且显式加载时才进入上下文。
- 这证明了资源是"按需"加载，而非在发现阶段一次性读入内存。
