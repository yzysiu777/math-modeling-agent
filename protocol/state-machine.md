# 工作状态机

## 合法状态

```text
intake
  -> routed
  -> frozen
  -> contracted
  -> baseline_ready
  -> model_ready
  -> validated
  -> reviewed
  -> revision_approved
  -> reproduced
  -> paper_ready
  -> pdf_qa_passed
  -> human_frozen
```

允许回退到任一更早状态，但必须创建新的 `state_event`，说明触发原因、受影响工件、旧状态和新状态。回退不是删除历史状态。

## 关键不变量

- `intake` 不能直接进入 `model_ready` 或 `paper_ready`；
- `routed` 必须带合法路由和路由依据；
- `frozen` 必须带输入清单和哈希；
- `baseline_ready` 之前不能声称复杂模型提升；
- `reviewed` 必须有非作者审核记录；
- `revision_approved` 必须有人工批准的发现和白名单；
- `paper_ready` 必须只有有证据的 claim；
- `human_frozen` 必须有人工签名，不能由 Codex 或 Claude 产生。

检查器 `scripts/check_transition.py` 拒绝非法跳转、缺少前置证据和模型自审自批。
