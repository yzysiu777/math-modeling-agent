# Claude 适配入口

Claude 使用仓库根目录的 `CLAUDE.md` 和 `prompts/claude/` 中当前节点提示词。每次
会话只处理 C1、C2 或 C3 之一，读取人工提供的精简审核包，输出挑战报告，不直接
改写案例或论文。
