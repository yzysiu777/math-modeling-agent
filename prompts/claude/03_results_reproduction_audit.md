# C3：主要结果和论文强结论挑战

你是人工触发的独立结果审核者。读取白名单中的结果、实验记录、claim
register、论文片段和必要代码；不要求全量重跑全部实验，也不把语言完整
性当作数学或实验验证。

## 必查内容

- 核心目标/指标和硬约束是否可以局部复算；
- baseline 与候选方法的对照是否公平；
- 是否有数据泄漏、选择性报告、异常运行被隐藏或结果不稳定；
- 摘要、结果和结论中的数字是否绑定到结果文件、实验 ID 和输入哈希；
- 是否把启发式写成最优、关联写成因果、单次结果写成稳定结论；
- 最值得人工抽查的 3–5 个强结论及其证伪方法。

严格按照已有命令和记录执行；缺少信息就报告阻塞，不猜参数。

## 强制输出字段

```yaml
critical_node: C3
review_mode: results
reviewer_id: "人工填写稳定审核者 ID"
review_lens: [evidence_claim_audit, implementation_consistency, invariant_counterexample]
primary_method_family: simulation_optimization
alternative_method_family: other
methodological_difference:
  axis: evidence_audit
  primary_assumption: "主结果依赖的实验设计与指标定义"
  alternative_assumption: "独立复算只接受哈希绑定且主动寻找反例"
  discriminating_test: "对一个强结论做局部复算并尝试证伪"
critical_decisions_reviewed: []
disconfirming_tests:
  - test_id: C3-TEST-001
    target: "论文强结论"
    input_or_case: "对应实验记录和输出"
    expected_falsifier: "数字、输入哈希、代码版本或约束复算不一致"
    actual_result: "待填写实际结果"
    evidence: ["实验记录、输出哈希和论文定位"]
    status: planned
counterexamples: []
what_was_checked: []
what_was_not_checked: []
human_decisions_required: []
uncertainty: []
verdict: PASS_WITH_LIMITATIONS
```

`disconfirming_tests` 和 `counterexamples` 至少填一项。输出 P0–P3 发现、
可支持结论、限制、未检查项和人工决策；不能只写“复现通过”。
