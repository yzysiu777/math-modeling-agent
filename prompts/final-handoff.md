# 交接给下一轮 Agent 的提示词

请先读取当前案例的 `AGENTS.md`、`case_manifest.yaml`、问题契约、claim register、最近运行记录、C1/C2/C3 审核、所有未解决 finding、`failures/`、论文状态和 `protocol/gates.md`。

先报告当前状态：路由、G0–G12、已支持结论、证据位置、未验证项、P0/P1 阻塞项、最近一次可信运行、C1/C2/C3 审核、R0–R3 修订回归、论文格式状态、AI 使用记录状态和下一步。不要从聊天记忆补造结论；以工作区工件、哈希和 Git 提交为准。发现结论与工件冲突时，先建立新的审查记录并暂停定稿。

若最近有修改，必须同时报告 `change_impact_record`、`revision_validation_record`
和 `human_review_card` 的路径、前后哈希、受影响 Gate、required check 退出码、
未关闭 finding 以及人工已检查/未检查范围。
