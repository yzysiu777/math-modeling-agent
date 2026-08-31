# 案例团队协作

一个案例装整道题。`sources.yaml`、`input/`、`checkpoint.yaml`、`decisions.md` 和 `paper/` 是共享
层；每天工作的硬范围是一个 `q<k>/`。同一时刻一份文件只有一个写入者。

## 文件分工

- Orchestrator：`sources.yaml` 协助、阶段 0、`checkpoint.yaml`、审核卡；
- Modeler：当前题 `brief.md`、`board.md`、`specs/`；
- Engineer：当前题 `code/`、`outputs/` 与 board 结果；
- Writer：`paper/sections/q<k>.tex` 与共享 `paper/claim_map.md`；
- Reviewer：只写本题 C1/C2 卡或共享 C3 卡，不改主解；
- 队员：人工专属 `decisions.md` 与最终提交。

`q<k>` 可读取 `q<j>/outputs/` 当且仅当 `j < k`。任何后题到前题的反向依赖都必须消除，不能
靠口头承诺。原始数据按阶段 0 生成的本题白名单只读。

## Git 与落盘交接

推荐分支仍按模型、分析、论文或审核任务命名。提交说明写改变、原因、验证和下一步。失败 Probe
留在 board；淘汰路线留在 brief；过程只追加到本题 log。不要复制外部开发控制台材料进案例。

生产角色均由队员人工启动并复用本题会话，固定 `gpt-5.6-sol`、`high`。Orchestrator 只输出
启动/继续提示词，不调用任务工具。Reviewer 由队员人工启动新会话，provider/model 不绑定厂商。

## 审核协作

C1 每题必做；C2 由检查器触发；C3 全案例一次。Reviewer 的唯一推荐动作默认执行，队员可否决；
拒绝 finding 才回原会话回签。独立性来自上下文隔离、最小材料、方法差异和证伪任务，不来自
身份签名、哈希链或某个指定厂商。
