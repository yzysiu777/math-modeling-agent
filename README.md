# 数学建模 Agent 工作台

一个案例装整道题：共享题面和数据来源，每个子问题有独立工作目录，后题可单向复用前题结果，
最后共享一份论文。

## 快速启用

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python scripts/create_case.py --case-id contest-a --questions 3
```

新案例初始 34 个文件：18 份工作文件加一套按问分章的论文骨架。没有空阶段报告，队员入口
不随题数增长。先编辑
`cases/contest-a/sources.yaml`：

```yaml
statement: /absolute/path/to/problem.pdf
data_roots:
  - /absolute/path/to/data
docs: []
questions:
  q1: 第一题
  q2: 第二题
  q3: 第三题
shared: [共享数据]
literature: /absolute/path/to/文献        # 可选
```

`statement` 可为 PDF、DOC/DOCX、Markdown、文本或目录。`docs: []` 会自动扫描数据根及父目录
的说明文件。原始数据不复制、不软链、不修改。

`literature` 是你自建的文献文件夹，可留空。阶段 0 会把里面的文献登记进
`paper/文献清单.md`；写作手联网检索到的补充文献登记在同一张表。**每一条的核对状态都留给你**，而且
不阻断流程 —— 脚本只保证「引用能追到账本」，真伪只有人能判，按你自己的节奏抽查。

## 阶段 0

```bash
make ingest CASE=cases/contest-a
```

它一次性生成带来源行的 `input/题面全文.md`、完整列名与缺测候选的 `input/数据清单.md`、
`input/说明文档/`、只列需人工判断异常的 `队员工作区/数据踏勘速览.md`、`paper/文献清单.md`，
以及每题 `q<k>/数据范围.md`。路径缺失、相对、不可读或题数不一致时直接失败。

## 目录

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

`q<k>` 只可引用编号更小的题目 outputs。跨题反向依赖会被唯一新增的 BLOCK 码拦截。

## 每题四步与时间盒

A 定题、B 试跑、C 出结果、D 写本题；最后 E 全案例收官。详细规则和时间盒见
`protocol/competition-workflow.md`。

`make case-check` 保留四个 STAGE 值：

| 工作步骤 | STAGE |
|---|---|
| A 与 B 前段 | `exploration` |
| B 末段与 C | `model_selection` |
| D | `paper_claims` |
| E | `final` |

## 审核

```bash
make review-packet CASE=cases/contest-a NODE=C1 QUESTION=q1
```

C1、C2 每题必做；C3 每题一次，全案例收官前再一次。审核者必须给唯一推荐
动作，生产角色默认执行，队员可否决。审核者保持新会话、最小材料、不同方法和反例任务，
provider/model 如实填写。

队员只需从 `队员工作区/现在做什么.md` 进入。该目录只保存指针和决策所需的最小上下文，
不复制 brief、board、SPEC 或审核卡正文；`我的笔记.md` 只由队员写。

## 常用命令

```bash
make spec-check CASE=cases/contest-a
make case-check CASE=cases/contest-a STAGE=exploration
make review-packet CASE=cases/contest-a NODE=C2 QUESTION=q1
make demos
make paper
make start-prompt CASE=cases/<case_id> ROLE=writer Q=q1   # 生成角色启动提示词
make paper CASE=cases/<case_id>          # 案例论文整本
make paper CASE=cases/<case_id> Q=q1    # 只编译某一题
make paper-ci
make final-check CASE=cases/contest-a
```

探索提醒不等于阻断；确定性错误、非法跨题依赖、触发但缺失的审核和最终 Claim 证据会阻断相应
边界。最终 PDF 和实际提交始终由队员确认。
