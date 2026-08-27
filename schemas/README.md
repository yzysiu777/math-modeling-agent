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

新增修订闭环记录：`change_impact_record`、`revision_validation_record`、
`human_review_card`。它们分别说明变更影响、定向验证和人工决策，不能互相
替代。
