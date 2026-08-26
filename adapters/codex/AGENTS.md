# Codex Adapter

将此文件复制到具体题目的案例根目录后使用。它把上级工作台的角色和门禁接到 Codex 的目录作用域规则。

开始前读取案例根目录的 `AGENTS.md`、`case_manifest.yaml`、`protocol/workflow.md` 和 `protocol/gates.md`；若本文件作为唯一规则文件，则再读取工作台中的：

`/Users/lambency/Desktop/数学建模/agent/AGENTS.md`

主角色使用：

`/Users/lambency/Desktop/数学建模/agent/roles/codex_lead.md`

需要 Claude 审查时，把原始输入、数据契约和指定工件交给独立审查链，不把 Claude 输出直接合并成主方案。任何最终结论必须回到案例工作区的 claim register、实验记录和审查报告。
