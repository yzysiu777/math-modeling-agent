# 风险台账

评分：概率和影响均为 1-5；风险分数为二者乘积。分数不替代 P0-P3 finding 严重度。

| ID | 风险 | 概率 | 影响 | 分数 | 触发信号 | 预防/控制 | Owner |
|---|---|---:|---:|---:|---|---|---|
| R-001 | 未知题被旧题型错误路由 | 5 | 5 | 25 | 输出出现患者、航迹、DAG 等无关概念 | 去硬编码、四态路由、人工覆盖 | Router |
| R-002 | 数据分析题发生标签或时间泄漏 | 4 | 5 | 验证分数异常、切分前全量拟合 | 泄漏检查、折内预处理、时间回测 | Data auditor |
| R-003 | 优化结果违反硬约束 | 4 | 5 | 论文有目标值但无 constraint report | 独立可行性检查和目标重算 | Optimization reviewer |
| R-004 | 启发式被写成全局最优 | 4 | 5 | 无证书/gap/证明却出现“最优” | claim language gate、求解器状态记录 | Paper reviewer |
| R-005 | Claude 盲审被污染 | 4 | 4 | reviewer 已看草稿却标记 blind | 审查 bundle、exposure declaration | Adversary owner |
| R-006 | Codex 与 Claude 一致被当作真值 | 3 | 5 | claim 证据仅为两个模型意见 | 至少一种外部/确定性证据 | Gatekeeper |
| R-007 | 多 Agent 同时修改共享文件 | 3 | 5 | 合并冲突、结果被覆盖 | 单写者、append-only 工件、任务锁 | Orchestrator |
| R-008 | 上下文增长导致规则遗忘 | 4 | 4 | 状态与文件冲突、重复劳动 | 状态快照、短交接、按需加载规则 | Orchestrator |
| R-009 | 多代理成本和时间失控 | 4 | 4 | 简单任务产生大量 workstream | 风险触发、多代理预算和停止条件 | Orchestrator |
| R-010 | Schema 可填但不可复现 | 4 | 5 | 缺命令、版本、种子、哈希 | v2 Schema + validator | Repro engineer |
| R-011 | 原始输入或运行被覆盖 | 3 | 5 | 同一路径内容改变 | 哈希、只读、append-only、版本管理 | Orchestrator |
| R-012 | 论文数字与最终结果不一致 | 4 | 5 | 手工复制、多份表格 | 单一结果源、claim-paper validator | Paper QA |
| R-013 | 官方规则使用二手或旧版本 | 3 | 5 | ACTIVE 指向镜像/2025 快照 | 官方 manifest、比赛日刷新 | Compliance owner |
| R-014 | AI 使用记录不满足当届规则 | 3 | 5 | 无工具版本、用途或人工核验 | 当届规则冻结、交互台账 | Human owner |
| R-015 | 最终 PDF 在 MD5 后被修改 | 2 | 5 | signoff hash 与上传文件不同 | FROZEN 状态、哈希比对 | Human owner |
| R-016 | 人工签署流于形式 | 3 | 5 | 签名不绑定工件和限制 | machine-readable signoff | Human owner |
| R-017 | 复杂模型掩盖 baseline 失败 | 4 | 4 | 无可解释基线直接调复杂模型 | G5 阻断 | Solution lead |
| R-018 | 相关性被写成因果 | 4 | 4 | 无识别策略却使用“导致” | 因果措辞 gate 和 reviewer | Data analyst |
| R-019 | Hybrid 点估计忽略不确定性 | 3 | 5 | 优化器只收到单一预测值 | 情景/区间/鲁棒集合接口 | Hybrid coordinator |
| R-020 | 目录无版本控制导致不可回滚 | 3 | 4 | 文件被直接覆盖 | 实施前 Git/快照 | Human owner |

## 最高优先级风险

1. R-001：范围污染；
2. R-002：数据泄漏；
3. R-003：不可行优化解；
4. R-010：伪复现；
5. R-012/R-013：论文数字和官方规则错误。

## 风险接受原则

- P0/P1 相关风险不能仅用“接受风险”绕过；必须修复、降级结论或停止推进。
- 成本和延迟风险可以通过减少候选与并行度控制，但不得降低数据、数学、复现和最终合规门槛。
- 无法消除的不确定性必须进入论文局限、交接和 human signoff。

