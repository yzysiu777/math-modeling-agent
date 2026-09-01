# 当前架构

## 粒度

案例粒度是整道题，执行粒度是子问题。`sources.yaml` 与 `input/` 共享；`q<k>/` 隔离每天的
brief、实验、规格、代码、结果、审核和日志；`paper/` 汇总全题。目录本身构成角色硬范围。

```text
sources.yaml ──阶段 0──▶ input/ + q1/数据范围.md ...
                              │
                    q1 ──▶ q2 ──▶ q3
                     └────────────▶ paper/claim_map.md ──▶ PDF
```

边只允许从小题号指向大题号。解析集中在 `scripts/case_paths.py`，跟随符号链接后仍必须留在案例
与正确 evidence root 内；后题产物不得成为前题证据。

## 角色

Modeler 维护本题 brief、board 与 Full SPEC；Engineer 维护本题 code 和 outputs；Writer 维护
本题论文章节与共享 claim map；Orchestrator 维护 checkpoint、阶段 0 和审核卡。角色按子问题
复用持续会话，Reviewer 在 C1/C2/C3 使用隔离新会话和最小材料。

## 确定性检查

- `case_sources.py` 校验唯一来源声明、绝对路径、可读性和题数目录一致性；
- `ingest.py` 抽取题面来源行、转写或登记说明文档、列全数据表头并生成白名单；
- `check_spec.py` 检查五段 Full SPEC、Probe 闭环和跨题方向；
- `check_case.py` 检查 C1、风险触发 C2、全案例 C3、确定性结果、Claim 与跨题方向；
- `make_review_packet.py` 从 `sources.yaml` 和当前题目录构造最小审核材料，旧案例才使用历史路径读法。

四个 STAGE 值只是检查强度，不是另一套流程。C2 的触发条件写死在检查器；C1 与 C3 的范围
固定。所有脚本只判断可见结构和已记录状态，不证明数学正确性。

## 证据边界

原始材料只读；Probe 先写判据；Champion 独立复算；关键 Claim 指向本题 outputs 和实验 ID。
Reviewer 可做决定但无编辑权；队员可否决；只有官方材料硬冲突、授权扩张、最终提交回人工。

## 设计来源

结构性改版来自真实比赛回放中的机制性观察：若预备扫描没有覆盖数据根旁的格式文档、无表头
记录的完整字段、空间与时间一致性和产品内部自洽性，昂贵审核会被迫补做本应自动完成的踏勘。
归档证据保留在外部只读实测记录中，运行协议不嵌入任何具体赛题名词。
