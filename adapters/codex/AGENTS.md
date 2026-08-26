# Codex Adapter

将此文件复制到案例根目录后使用。它把工作台规则接入 Codex 的目录作用域。

开始前读取案例的 `AGENTS.md`、`README.md`、`case_manifest.yaml`、`protocol/workflow.md` 和 `protocol/gates.md`。主角色使用 `roles/solution_lead.md`；根据 `routing_record` 加载 `optimization_modeler.md`、`data_analyst.md` 或混合接口检查。

Codex 可以创建模型、代码、实验和论文源文件，但不能自批高风险结论。每个重要结果必须回到案例的 claim register、实验记录、审核记录和复现记录。需要 Claude 时，按 `prompts/claude/` 生成审查包，不能把 Claude 输出未经批准地合并到主方案。
