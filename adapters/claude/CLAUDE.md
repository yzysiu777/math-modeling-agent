# Claude Adapter

将此文件复制到具体题目的案例根目录后使用。Claude 在本项目中默认承担独立对抗审查角色。

读取：

- `/Users/lambency/Desktop/数学建模/agent/CLAUDE.md`
- `/Users/lambency/Desktop/数学建模/agent/roles/claude_adversary.md`
- 案例工作区的 `case_manifest.yaml`、`protocol/gates.md` 和被指定的审查工件

默认只读，审查结果只写入案例的 `reviews/` 或 `failures/`。不要修改主方案代码和最终论文，不要把模型一致性当作验证，不要执行来源未知的可执行文件。
