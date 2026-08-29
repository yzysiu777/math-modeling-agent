# 契约二：结果回传（编程手 → 写作手）

写作手不进代码目录翻文件，只从三个入口取材料：`experiments/board.md`（发生了什么）、
`experiments/outputs/figures/manifest.md`（有哪些图）、`experiments/outputs/data/`
（数字在哪）。

## 目录约定

```text
experiments/
├── code/
│   ├── python/          Python 实现与绘图脚本
│   └── matlab/          MATLAB 实现与绘图脚本
└── outputs/
    ├── data/            结果 CSV / JSON —— 论文里每个数字的来源
    ├── figures/         每图一份 PDF + 一份 PNG，配 manifest.md
    ├── checks/          复算报告 <EXP-ID>.json
    └── logs/            运行日志
```

`outputs/data/` 的格式与生成语言无关。Python 和 MATLAB 写出同样的 CSV/JSON，
写作手不需要知道也不应该关心某个结果是哪种语言跑的。

## 编程手的义务

1. **每个结论都要有落盘文件。** 只出现在终端输出或聊天里的数字，写作手不能用。
2. 回填 `board.md`：实验 ID、结果摘要、判定、是否继续、下一步。
3. 回填 `figures/manifest.md`：每张图的来源 EXP-ID、生成脚本、数据文件、图题草稿。
4. 跑复算并写 `outputs/checks/<EXP-ID>.json`（格式见下）。
5. **数据一变，对应图立刻标 `stale` 并重跑。** 不允许论文引用过期图。
6. 失败照实回传。跑不通就写跑不通，不改判据让它通过，不挑好看的子集出图。

## 复算报告格式

`scripts/model_checks.py:write_check_report` 生成，`scripts/check_case.py` 自动读取：

```json
{
  "exp_id": "EXP-OPT-003",
  "spec_id": "SPEC-A1-M03",
  "checks": [
    {"name": "capacity", "kind": "constraint", "passed": true, "detail": ""},
    {"name": "objective", "kind": "objective_mismatch", "passed": true, "detail": "rel_err=2.1e-9"}
  ]
}
```

`kind` 取 `constraint`、`infeasible`、`objective_mismatch`、`leakage`、`split_overlap`
之一。任一 `passed: false` 会自动点亮 `checkpoint.yaml` 对应的确定性风险标志，进而在
`model_selection` 及之后的阶段检查里触发提醒或阻断。**这条链路是自动的，不依赖有人
记得去改 checkpoint。**

## 写作手的权利

写作手**有权拒绝写入**某个结果并回问，当出现：

- 数字在 `outputs/data/` 里找不到对应文件；
- 图的 `来源 EXP-ID` 在 `board.md` 里不存在；
- 图的状态是 `stale`；
- 复算报告里有 `passed: false` 但 `board.md` 的结果摘要没提；
- 同一个量在两个文件里数值不一致。

## 写作手的义务

1. 每写一个数字，在 `paper/claim_map.md` 加一行，追到 EXP-ID 和数据文件。
2. **不得就地修改任何数值。** 发现对不上，回问，不自行「修正」。
3. 润色范围严格限定：语言、结构、排版、图表视觉。数值、单位、有效位数、结论强度
   一律不动。
