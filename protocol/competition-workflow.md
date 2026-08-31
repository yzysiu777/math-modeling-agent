# 按子问题循环的轻量竞赛流程

本工作台只有这一套流程。每个子问题依次完成 A–D，最后全案例执行一次 E；研究性深化是在当前
步骤增加实验，不切换模式。时间盒是超时提醒，不是门禁。

## 阶段 0：全案例预备处理

队员只填写 `sources.yaml`，Orchestrator 运行一次 `make ingest`。脚本校验绝对路径与可读性，
转写完整题面并记录来源行，扫描数据根和父目录的说明文件，列出每个数据文件的大小、行数、
完整列名、编码和缺测候选值，再按 `questions` 与 `shared` 生成每题白名单。

阶段 0 不复制原始数据。无内嵌表头的格式必须结合转写说明核对，不能静默省略列。

## A 定题（不超过 2 小时）

当前 `q<k>/brief.md` 一次完成：题意、目标、硬约束、单位与交付物；无评价发散至少六条想法；
保留至少三条方法论不同路线；按效果、实现成本、运行成本、数据满足度、可解释性、论文价值、
主要风险七维度比较；选择 Champion/Challenger 与路由。

C1 每题必做。A 结束必须完成本题 C1。Reviewer 先读原始题面与说明，再读 brief；卡中有节点决定且写明推荐
路由，即完成路由确认，无需第二次签字。

## B 试跑（不超过 2 小时）

Modeler 在 `q<k>/board.md` 写 2–3 行便宜 Probe：先填假设、判据、范围、预算，再运行并写
PASS/FAIL。只为进入正式实现的路线写一份五段 Full SPEC。B 结束时至少一条 Champion Probe
为 done+PASS，且 `make spec-check` 通过。

## C 出结果（不超过 4 小时）

Engineer 按 Full SPEC 实现、统一比较并把 data/checks/figures 写入本题 outputs。Champion 的
约束、目标、切分、泄漏与关键指标使用独立路径复算。

C2 仅在以下任一条件成立时阻断 `model_selection`：

1. Champion 没有任何 `status=done` 且判定 PASS 的 Probe；
2. 同一路线至少出现两行 `status=failed`；
3. Full SPEC 的 `probe_result` 为 `WAIVED` 或 `PENDING`。

全假时检查器输出 REMINDER，并要求在 `q<k>/log.md` 记一行跳过理由。

## D 写本题（不超过 2 小时）

Writer 只从 Full SPEC、board、outputs 与复算报告写 `paper/sections/q<k>.tex`，并在全案例
`paper/claim_map.md` 增加本题关键 Claim。普通表格由数据生成，不逐数登记。证据不足时降低
“最优”“因果”等表述强度。

## E 全案例收官

全部子问题完成后只做一次 C3，从 claim map 抽查 3–5 条最高风险强结论。随后统一核数、术语、
图表、引用、匿名、官方格式和 PDF，运行 `make final-check`。最终文件确认与实际提交必须等待队员。

## STAGE 对照

| 工作步骤 | `make case-check` 的 STAGE |
|---|---|
| A 与 B 前段 | `exploration` |
| B 末段与 C | `model_selection` |
| D | `paper_claims` |
| E | `final` |

不新增 STAGE。四个值只控制提醒何时升级为阻断。

## Reviewer 决策规则

每条 finding 写唯一 `推荐动作：`、一句证据理由、一次优项，并标 `默认执行`。不得列多个选项
让队员挑。队员不回应，生产角色按推荐实施；队员可否决，拒绝 finding 时回原 Reviewer 会话
回签一次。`GO_WITH_FIXES` 是可执行状态，不等待额外“批准”。

当同一观测量的两个来源相距过远、点对点配对不成立时，Reviewer 应直接判定并推荐证据最稳的
单源或降级方案，不得把方案清单退回队员。

Reviewer 仍保持新会话、最小审核包、先读原始证据、方法论不同和反例任务；不修改主解、不启动
其他 Agent、C3 不代写论文。`Human-only block` 只限官方材料硬冲突、授权范围扩张、最终提交。

## 每题日志与回报

每步在本题 `log.md` 追加四行：做了什么、产物路径、风险、下一步。普通每轮只输出六行 Agent
回报卡；跨角色时才补材料、范围和完成标准。不建立七份阶段报告、审核摘要副本或普通决策日志。
