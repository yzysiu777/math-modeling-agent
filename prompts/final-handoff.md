# 数学建模案例交接提示词

请以当前案例文件和最近一次 Git 提交为事实源，先读取 `AGENTS.md`、`README.md`、
`sources.yaml`、`checkpoint.yaml`、各题 `brief.md`、`board.md`、`log.md`、Full SPEC、outputs、
`decisions.md`、C1/C2/C3 审核卡、共享 claim map 和论文状态。

输出：

- 当前路由和题意中仍不确定的部分；
- 三条以上候选路线、Champion、Challenger 及淘汰理由；
- 最近实验、统一比较口径、关键数字和可复算入口；
- 已完成/未完成的数值、数据、论文和格式检查；
- Independent Reviewer 检查了什么、没有检查什么、给出的唯一推荐动作，以及审核 provider、
  model、fresh session 和是否看过主会话的元信息；
- 论文当前章节、图表、引用和 AI 使用记录状态；
- 下一项信息价值最高的实验；
- 仅三类人工专属边界中仍需队员决定的事项。

不要从聊天记忆补造结果，不要把单次输出写成稳定结论，不要删除失败路线。
