# 状态机与质量门禁

## 1. 状态

```text
NEW
  → SCOPE_APPROVED
  → INPUTS_FROZEN
  → ROUTED
  → CONTRACT_READY
  → BASELINE_READY
  → CANDIDATES_READY
  → DETERMINISTICALLY_VALIDATED
  → ROBUSTNESS_VALIDATED
  → ADVERSARIALLY_REVIEWED
  → REPRODUCED
  → PAPER_READY
  → FINAL_QA
  → FROZEN
```

旁路状态：

- `NEEDS_HUMAN`：存在必须由人决定的歧义或取舍；
- `BLOCKED`：P0/P1 或必要输入缺失；
- `REJECTED`：路线被反例、数据、推导或复现否定；
- `PAUSED`：预算、时间或外部资源暂不可用；
- `ARCHIVED`：保留但不再推进。

`PAUSED` 不是 `BLOCKED`；`REJECTED` 不能通过改名重新激活，必须创建新路线 ID。

## 2. 16 个 Gate

| Gate | 名称 | 负责人 | 最低通过证据 | 失败动作 |
|---|---|---|---|---|
| G0 | 目标与授权 | Human owner | 目标、范围、禁止项、期限、交付 | `NEEDS_HUMAN` |
| G1 | 题意与路由 | Router + human review | problem contract、routing record | 退回 Intake |
| G2 | 来源与输入冻结 | Orchestrator | manifest、来源、哈希、只读策略 | `BLOCKED` |
| G3 | 数据质量与合同 | Data auditor | 字典、粒度、主键、质量和泄漏预检 | 修复数据合同 |
| G4 | 假设与符号 | Domain reviewer | 假设依据、影响、敏感性计划、符号单位 | 降级/补证据 |
| G5 | Baseline | Domain modeler | 可运行简单基线、小例子、日志 | 不得启动复杂比较 |
| G6 | 模型/公式/约束 | Independent reviewer | 目标、变量、约束、代码映射 | `BLOCKED` |
| G7 | 算法和实现正确性 | Deterministic validator | 单测、边界、终止、复杂度、版本 | 修复并新 run ID |
| G8 | 可行性与结果边界 | Validator + reviewer | 约束检查、目标重算、区间/误差 | 降级 claim |
| G9 | 结果可信度 | Domain reviewer | 对照、指标、统计或求解器证据 | 补实验 |
| G10 | 敏感性与稳健性 | Domain reviewer | 扰动、种子、情景、规模和失效边界 | 限制披露/补跑 |
| G11 | 对抗审查与复现 | Independent adversary | 无未解决 P0/P1、复现记录 | `BLOCKED` |
| G12 | 论文证据与引用 | Paper/citation reviewer | claim-to-paper、来源、数字和图表映射 | 退回写作 |
| G13 | 官方格式与 AI 合规 | Compliance reviewer | 当届规则 manifest、AI 记录 | `BLOCKED` |
| G14 | 最终 PDF QA | Formatting QA | 渲染、元数据、匿名、哈希 | 重新导出 |
| G15 | 人工签署与冻结 | Human owner | signoff 绑定最终哈希和限制 | 不得提交 |

任何 Gate 的作者和批准者不能相同。G15 只能由人完成。

## 3. 合法转换

状态转换必须由 `state_event` 触发：

```yaml
schema_version: "2.0"
event_id: "EVT-YYYYMMDD-0001"
project_id: ""
from_state: ""
to_state: ""
gate: ""
actor: ""
actor_role: ""
artifact_hashes: []
open_findings: []
reason: ""
timestamp: ""
```

禁止直接编辑当前状态；当前状态由 append-only 事件重放得到。为了快速恢复，可以生成 snapshot，但 snapshot 必须绑定最后一个 event ID 和事件日志哈希。

## 4. 失效传播

| 变更 | 必须重新打开的 Gate |
|---|---|
| 题意或交付变化 | G1-G15 |
| 原始文件变化 | G2-G15 |
| 数据字典、标签、切分变化 | G3、G5-G15 |
| 假设变化 | G4-G15 |
| 目标、变量或硬约束变化 | G5-G15 |
| 代码、依赖、求解器变化 | G7-G15 |
| 评价指标变化 | G9-G15 |
| 论文表述变化但结果不变 | G12-G15 |
| 官方规则变化 | G13-G15 |
| 最终 PDF 任意字节变化 | G14-G15 |

## 5. 暂停与恢复

暂停时必须写：

- 当前 state 和最后 event；
- 已冻结工件及哈希；
- 正在运行的任务和是否可安全中断；
- 未解决 finding；
- 预算、时间和外部依赖；
- 恢复后的第一条确定性检查。

恢复时不得从聊天记忆补造状态。必须读取 event log、snapshot、artifact registry、最近运行和未解决审查；验证哈希后再继续。

## 6. 重试与失败

- 工具或网络瞬时失败：同一任务最多按配置重试；
- 数学、数据或可行性失败：不得当作瞬时错误重试，必须进入 failure record；
- 修改后生成新 run ID，不覆盖失败运行；
- reviewer 的 P0/P1 只有原 reviewer 或 human owner 能关闭；
- 关闭必须引用新工件和验证结果。

## 7. 冻结

`FROZEN` 必须同时绑定：

- 最终 PDF SHA-256/MD5；
- 源文件和结果清单哈希；
- G0-G15 快照；
- human signoff；
- AI 使用记录版本；
- 当届官方规则 manifest。

冻结后任何字节变化都生成新版本并重新通过 G14-G15。

