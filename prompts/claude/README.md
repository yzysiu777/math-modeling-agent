# Claude 交接提示词目录

这里的提示词对应“先审后改”两阶段流程。Claude 只审核 C1、C2、C3
三个关键节点；每次使用时复制一份到审核会话，补充案例 ID、审核 ID、
文件白名单、输入哈希和验收标准。

| 文件 | 用途 | 是否可修改主方案 |
|---|---|---|
| `01_blind_problem_review.md` | C1：题意、目标和约束盲审 | 否 |
| `02_data_model_audit.md` | C2：模型架构和算法挑战 | 否 |
| `03_results_reproduction_audit.md` | C3：主要结果和论文强结论挑战 | 否 |
| `05_approved_revision.md` | 人工批准后的受限修订提案 | 只能输出 patch |

Claude 的报告进入 `reviews/`；修订提案进入 `reviews/<review-id>/proposed.patch`，
不得直接写入 `main`。LaTeX 只在 C3 的强结论和证据范围内审核，普通排版
由确定性检查器和 R0/R1 规则处理。

`../claude-blind-review.md` 仅是重定向入口，不是第四个审核节点。所有审核
报告必须使用 `schemas/review_record.schema.json` 的结构化字段，尤其是稳定
`reviewer_id`、规范方法族和带实际结果的可证伪测试。
