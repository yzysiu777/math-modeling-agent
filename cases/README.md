# 案例目录约定

案例目录只保存比赛运行时资料，不保存外部 Planner/Executor 开发控制面。创建案例：

```bash
python3 ../scripts/create_case.py --case-id your-case --route insufficient_information
```

脚本会生成下面的完整骨架，队员只需要填 `case_brief.md`：

```text
cases/<case_id>/
├── input/                    题面和附件，只读
├── case_brief.md             队员唯一需要填的启动文件
├── checkpoint.yaml           路由确认、审核状态与确定性风险标志
├── models/{candidates,comparison}.md
├── specs/                    建模手 → 编程手的实现规格与回问
├── experiments/
│   ├── board.md
│   ├── code/{python,matlab}/
│   └── outputs/{data,figures,checks,logs}/
├── decisions.md
├── reviews/{,packets/}
└── paper/claim_map.md        论文数字溯源表
```

## 三个角色写哪些文件

| 目录 | 主要写入者 | 其他角色 |
|---|---|---|
| `models/`、`specs/` | 建模手 | 编程手与写作手均只读；要改就回问 |
| `experiments/code/`、`experiments/outputs/` | 编程手 | 写作手只读 `outputs/`、`board.md` 和 `checks/`，不进 `code/` |
| `paper/`、`claim_map.md` | 写作手 | 只读 |
| `decisions.md`、`checkpoint.yaml` | 队员 | 角色可提议，不代替确认 |
| `reviews/` | 队员粘贴审核报告 | `packets/` 由 `make review-packet` 生成 |

同一时间只让一个角色写工作树。

## 检查

```bash
make spec-check CASE=cases/<case_id>
make case-check CASE=cases/<case_id> STAGE=exploration
make case-check CASE=cases/<case_id> STAGE=model_selection
make case-check CASE=cases/<case_id> STAGE=paper_claims
make final-check CASE=cases/<case_id>
```

`REMINDER` 允许继续普通探索；`BLOCK` 表示当前阶段不能冻结路线、写入强结论或提交。
`checkpoint.yaml` 记录少量阶段和风险标志，它不是身份认证或审批系统；其中的确定性风险
标志优先由 `experiments/outputs/checks/*.json` 的复算结果自动点亮。

每个案例可以根据题目增加本地字段和脚本，但不要把多个题目的数据混在同一目录。
