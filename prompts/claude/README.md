# Claude 交接提示词目录

这里的提示词对应“先审后改”两阶段流程。每次使用时复制一份到审核会话，补充案例 ID、审核 ID、文件白名单、输入哈希和人工批准信息。

| 文件 | 用途 | 是否可修改主方案 |
|---|---|---|
| `01_blind_problem_review.md` | 独立重构题意和风险 | 否 |
| `02_data_model_audit.md` | 数据、假设、模型和约束审计 | 否 |
| `03_results_reproduction_audit.md` | 结果、稳健性和复现审计 | 否 |
| `04_latex_paper_audit.md` | 论文内容、引用、AI 合规和排版审计 | 否 |
| `05_approved_revision.md` | 人工批准后的受限修订提案 | 只能输出 patch |

Claude 的报告进入 `reviews/`；修订提案进入 `reviews/<review-id>/proposed.patch`，不得直接写入 `main`。
