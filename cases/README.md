# 案例目录约定

一个案例装整道题，共享来源与论文，每个子问题一个硬范围目录：

```bash
python3 ../scripts/create_case.py --case-id your-case --questions 3
```

```text
cases/<case_id>/
├── sources.yaml
├── checkpoint.yaml
├── decisions.md
├── input/{题面全文.md,数据清单.md,说明文档/}
├── 队员工作区/{现在做什么.md,数据踏勘速览.md,审核卡索引.md,我的笔记.md,待批准/,已批准/,启动提示词/}
├── q1/ q2/ q3/
│   ├── brief.md
│   ├── 数据范围.md
│   ├── board.md
│   ├── specs/
│   ├── code/{python,matlab}/
│   ├── outputs/{data,checks,figures}/
│   ├── reviews/
│   └── log.md
└── paper/{claim_map.md,reviews/,sections/}
```

先填写 `sources.yaml`，再运行：

```bash
make ingest CASE=cases/<case_id>
```

阶段 0 生成题面来源行、说明文档登记、完整数据清单、只列异常的 `数据踏勘速览.md` 和每题
白名单。原始数据保持原位只读。

## 写入者与依赖方向

Modeler 写本题 brief/board/specs；Engineer 写本题 code/outputs；Writer 写本题章节与共享 claim map；
Orchestrator 写 checkpoint、审核卡和 `队员工作区/`；`我的笔记.md` 是唯一例外，AI 只读。
队员工作区不复制 brief、board、SPEC 或审核卡正文，也不按题或步骤建子目录。`q<k>` 只可
使用 `q<j>/outputs/` 且 `j < k`。

每题 log 是唯一过程记录，每步追加“做了什么 / 产物路径 / 风险 / 下一步”。不建七份阶段报告。

## 检查

```bash
make spec-check CASE=cases/<case_id>
make case-check CASE=cases/<case_id> STAGE=exploration
make case-check CASE=cases/<case_id> STAGE=model_selection
make case-check CASE=cases/<case_id> STAGE=paper_claims
make final-check CASE=cases/<case_id>
```

STAGE 对应 A/B 前段、B 末/C、D、E；它们不是另一套流程。C1 每题必做，C2 按风险触发，C3
全案例一次。最终提交由队员确认。
