# 记录接口

本目录中的 `*.schema.json` 是机器可读的 JSON Schema；`templates/` 中的 YAML 是可复制的案例记录样例。所有记录必须包含 `record_type`、稳定 ID、创建者、时间、证据或不确定性字段，并通过 `scripts/validate_workspace.py` 检查。

记录采用 `zh-human-readable-en-schema`：人类说明可以使用中文，字段名、状态、路由、严重度和 Gate 使用固定英文枚举。

重要不变量：

- 作者不能批准自己写出的审核；
- 没有 `approved_findings` 不能进入 Claude 修订阶段；
- 没有输入哈希、代码版本和实验记录的结论不能进入强论文表述；
- C1/C2/C3 审核必须记录方法论差异、反例/可证伪测试、已检查和未检查范围；
- `change_impact_record` 与 `revision_validation_record` 必须使用安全检查 ID，不能保存待自动执行的 shell 命令；
- `human_review_card` 和 `human_signoff` 必须记录人工检查范围、未检查项和能力边界；
- `human_signoff` 只能由人工产生。
- `revision_validation_record.check_results` 必须来自固定可信运行器，包含执行时间、
  stdout/stderr 路径与哈希、退出码和实际输出哈希；旧的 `check_exit_codes`/
  `check_outputs` 不能作为证据。
- `approved_findings` 的案例、审核、修订、基线和结果 revision 必须严格关联；
  已批准/已应用记录的文件白名单和验证清单不能为空。
- `work_item` 固定单一写入者，执行者不能自审；`accepted` 只关闭工作项，不产生 G12。
- C1/C2/C3 审核必须使用 `input_bindings` 逐项绑定真实工作区文件、SHA-256 和
  `artifact_kind`；裸 `input_hashes`、全零占位哈希、缺失文件或错误哈希均不能通过。
- `target_revision` 标识案例修订，`target_git_revision` 必须是可达且与结果提交一致的
  完整 Git commit SHA。

新增修订闭环记录：`change_impact_record`、`revision_validation_record`、
`human_review_card`、`work_item`。它们分别说明变更影响、定向验证、人工决策和
案例协作状态，不能互相替代。`check_evidence_graph.py` 负责重要 claim 的
输入—代码—实验—输出—图表—论文证据链。
