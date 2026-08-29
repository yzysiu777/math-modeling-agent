# 案例目录约定

案例目录只保存比赛运行时资料，不保存外部 Planner/Executor 开发控制面。创建案例
时只需复制 [../templates/case_brief.md](../templates/case_brief.md)，或直接运行：

```bash
python3 ../scripts/create_case.py --case-id your-case --route insufficient_information
```

推荐结构见根目录 [README.md](../README.md)。`input/` 中的题面和附件只读；模型候选、
实验板、决定、C1/C2/C3 报告和论文源文件与案例一起维护。创建案例时会额外生成
`checkpoint.yaml`，由队员确认 router 建议的正式路由，并记录少量阶段和风险标志；它
不是身份认证或审批系统。每个案例可以根据题目
增加本地字段和脚本，但不要把多个题目的数据混在同一目录。

按赛程运行阶段检查：

```bash
make case-check CASE=cases/<case_id> STAGE=exploration
make case-check CASE=cases/<case_id> STAGE=model_selection
make case-check CASE=cases/<case_id> STAGE=paper_claims
make final-check CASE=cases/<case_id>
```

`REMINDER` 允许继续普通探索；`BLOCK` 表示当前阶段不能冻结路线、写入强结论或提交。
