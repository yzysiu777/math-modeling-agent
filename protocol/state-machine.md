# 单一竞赛状态机

`scripts/gate_contract.py` 是机器可读的唯一状态/Gate 合同。本文件只解释
状态含义，不建立第二套比赛流程。

## 主状态

```text
intake -> routed -> frozen -> contracted -> baseline_ready -> model_ready
  -> validated -> results_verified -> reviewed -> gate_passed -> paper_ready
  -> format_checked -> pdf_qa_passed -> human_frozen
```

### Gate 合同镜像

这是 `scripts/gate_contract.py` 的完整镜像，名称、进入状态、退出证据和顺序
不得只在本文件中单独修改。

| Gate | 名称 | 进入状态 | 首次通过的退出证据 |
|---|---|---|---|
| G0 | 目标、题意与权限 | `routed` | 人工确认目标、交付物和权限边界 |
| G1 | 输入和数据冻结 | `frozen` | 输入清单、来源、只读状态和哈希 |
| G2 | 数据契约、假设、符号和指标 | `contracted` | 数据/模型契约、假设表和指标定义 |
| G3 | Baseline | `baseline_ready` | 可解释 baseline、小案例和运行记录 |
| G4 | 正式模型和算法 | `model_ready` | 公式、算法、代码版本和参数记录 |
| G5 | 正确性、可行性与边界 | `validated` | 手算/穷举、维度、约束和边界检查 |
| G6 | 结果可信度与稳健性 | `results_verified` | 对照、复算、敏感性和稳健性证据 |
| G7 | 独立审核 | `reviewed` | C1/C2/C3 审核记录和未解决问题 |
| G8 | 修订与回归 | `gate_passed` | 变更影响、定向验证和关闭记录 |
| G9 | 论文证据绑定 | `paper_ready` | claim—实验—图表—引用映射 |
| G10 | 官方格式和 AI 合规 | `format_checked` | 当届规则、匿名和 AI 记录预检 |
| G11 | LaTeX/PDF 检查 | `pdf_qa_passed` | 编译、文本、元数据、渲染和 PDF 哈希 |
| G12 | 人工冻结 | `human_frozen` | 人工 signoff、最终提交文件和版本冻结 |

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
- `validation_passed`：所有 required checks 有可信运行器记录、退出码 0、日志哈希和输出证据，
  且 Git diff/逐文件 before-after 哈希通过公共事实校验；实现型检查已由 base commit
  的受保护 runner 重跑并与记录摘要一致；
- `validation_failed`：至少一项检查失败，不能关闭相关 finding；
- `restore_affected_gate`：只恢复受影响 Gate，并保留回退历史。R0 可在
  `affected_gates: []` 下恢复，但必须有 `gate_impact: no_gate_impact` 的显式证据。

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
