# 案例目录约定

每个竞赛案例使用 `cases/<case_id>/`，并在其中保存该案例自己的
`case_manifest.yaml` 与 `coordination/`。原始数据、运行缓存和私有审核包
默认按根目录 `.gitignore` 处理；需要协作的工作项、审核报告和可信证据必须
遵循 [../protocol/team-collaboration.md](../protocol/team-collaboration.md)。

这里不存放开发阶段的外部 Planner/Executor 控制面文件，也不复制跨案例的
交接单或历史审核记录。
