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

STAGE 对应 A/B 前段、B 末/C、D、E；它们不是另一套流程。C1、C2 每题必做，C3 每题一次、
全案例收官前再一次。最终提交由队员确认。

## 论文与文献

`paper/` 由 `create_case` 播种成一套官方版式的按问分章工程，写作手只填章节，不新建主文档。
`paper/文献清单.md` 是引用的唯一账本：阶段 0 把 `sources.yaml` 的 `literature` 文件夹登记为
`人工放入`，写作手联网检索的登记为 `联网检索`，每行写清支撑论断。核对状态是队员的抽查清单，不阻断流程。
没通过 C1 的子问题在各章里保持 `% <<Qk-SEALED>>` 封存，不得提前书写。

```bash
make paper CASE=cases/<case_id> Q=q1                      # 单题编译
make start-prompt CASE=cases/<case_id> ROLE=writer Q=q1   # 生成启动提示词
```
