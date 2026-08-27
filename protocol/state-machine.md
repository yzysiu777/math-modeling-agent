# 单一竞赛状态机

`scripts/gate_contract.py` 是机器可读的唯一状态/Gate 合同。本文件只解释
状态含义，不建立第二套比赛流程。

## 主状态

```text
intake -> routed -> frozen -> contracted -> baseline_ready -> model_ready
  -> validated -> results_verified -> reviewed -> gate_passed -> paper_ready
  -> format_checked -> pdf_qa_passed -> human_frozen
```

状态与 Gate 的对应关系：

| 状态 | 由哪个 Gate 产生 | 含义 |
|---|---|---|
| `intake` | 初始状态 | 尚未通过 G0 |
| `routed` | G0 | 目标、题意和权限已确认 |
| `frozen` | G1 | 输入和来源已冻结 |
| `contracted` | G2 | 数据/模型契约、假设和指标已固定 |
| `baseline_ready` | G3 | baseline 有运行和小案例证据 |
| `model_ready` | G4 | 正式模型和算法已有记录 |
| `validated` | G5 | 正确性、可行性和边界已检查 |
| `results_verified` | G6 | 结果复算、对照和稳健性已有证据 |
| `reviewed` | G7 | C1/C2/C3 独立审核已记录 |
| `gate_passed` | G8 | 无待回归变更，或局部修订已关闭 |
| `paper_ready` | G9 | 论文证据绑定完成 |
| `format_checked` | G10 | 当届格式和 AI 合规预检完成 |
| `pdf_qa_passed` | G11 | LaTeX/PDF 检查和哈希完成 |
| `human_frozen` | G12 | 人工签字并冻结最终版本 |

## 修订状态

任一已通过 Gate 发现变更时，不把无关 Gate 退回，而在当前记录中追加：

```text
gate_passed
  -> revision_pending
  -> impact_classified
  -> targeted_validation
  -> validation_passed | validation_failed
  -> restore_affected_gate
  -> gate_passed
```

- `revision_pending`：提出修改但尚未判断影响；
- `impact_classified`：已有 R0/R1/R2/R3 和受影响工件；
- `targeted_validation`：安全检查 ID 已生成并执行；
- `validation_passed`：所有 required checks 有退出码 0 和输出证据；
- `validation_failed`：至少一项检查失败，不能关闭相关 finding；
- `restore_affected_gate`：只恢复受影响 Gate，并保留回退历史。

R0 不得退回模型阶段；R1 不自动重跑实验；R2 需要相关代码测试、实验和
claim 处理；R3 需要数据/模型契约、可行性、目标复算、实验、稳健性和
人工/独立审核关闭。

## 不变量

- 非法主流程跳转和跳过前置证据会被拒绝；
- 修订状态不能绕过 `targeted_validation`；
- 影响等级、受影响 Gate 和 required checks 必须一致；
- `allowed_files` 为空时任何受限修订均失败；
- P0/P1 不能由提出者或修改者自行关闭；
- `human_frozen` 只能由 `human`/`human_owner` 产生；
- 回退、失败和恢复都生成新的 `state_event`，不删除历史。
