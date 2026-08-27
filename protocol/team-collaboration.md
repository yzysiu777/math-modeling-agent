# 案例级团队协作契约

本契约只约束主程序仓库内的案例协作目录。开发阶段的 Planner/Executor
控制面、交接单和审核报告保存在仓库外，不能复制到主程序仓库，也不能由
竞赛运行时自动加载。案例内只允许保存面向该案例的最小协作记录：

```text
cases/<case_id>/
├── case_manifest.yaml
└── coordination/
    ├── work-items/
    ├── reviews/
    └── evidence/
```

## 角色与写入边界

固定角色只有四类：

- `human_owner`：最终目标、取舍、签字和 G12 冻结者；
- `planner_reviewer`：拆分工作项、定义验收条件和独立审核；
- `executor`：只写获授权的工作项文件范围和结果证据；
- `independent_challenger`：只读复核、反例和复现证据，不修改被审方案。

每个工作项必须指定一个 `write_owner_id`，且它必须等于 `executor_id`。
同一时间处于 `executing` 或 `review_ready` 的工作项，允许文件范围不得重叠。
执行者不能担任该工作项的 reviewer；自我评价、模型意见一致和“看起来合理”
都不能替代证据。

## 工作项生命周期

```text
proposed -> approved -> executing -> review_ready
                         -> accepted | revision_requested | blocked
```

`accepted` 只表示该工作项满足其自身的验收条件，不自动产生 `human_frozen`；
G12 仍需单独的人类 signoff。`accepted` 必须带源提交、结果提交、每个
required check 的哈希证据、无未解决 P0/P1，并能由另一位成员复核。

工作项至少包含：目标、范围、非目标、允许文件、变更表面、R0–R3、受影响
Gate/claim/experiment、required check、执行者、审核者、单一写入者、源/结果
Git revision、测试证据、未解决项和人工决策项。

## 批处理与关键审核

多个 R0/R1 工作项可以批量提出，但每项仍需独立的文件范围和证据。涉及核心
数据、模型、实验逻辑、目标或约束的变更，继续使用 C1/C2/C3；本契约不增加
新的 Gate 或审核节点。Claude 的结果只能作为独立挑战输入，人工批准后才能
进入受限修订。

## 两个可复制的短提示词

### Human → Executor

```text
你是本工作项的 executor。只读取案例的 AGENTS/README、case_manifest、该 work item
和白名单文件；先核对 source_git_revision，再按 change_surfaces 和 required_checks
执行。只修改允许范围，保存可信检查证据和哈希，写入 coordination/ 的结果报告，
提交到指定分支。不要修改控制面、main 或未授权文件；完成后报告 result_git_revision、
测试证据、未解决项和人工决定。
```

### Human → Reviewer

```text
你是本工作项的 independent_challenger。只读检查 work item、executor 报告、差异、
证据哈希和结果；核对 source/result revision、每个 required check、P0/P1 和自我审核
限制。不要修改、推送、合并或创建标签；输出结构化 review_record，明确 PASS、阻塞项、
反例、未检查范围和需要 human_owner 决定的事项。
```
