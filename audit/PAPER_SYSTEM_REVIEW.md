# 论文系统审核与目标方案

## 1. 总结

现有 `writing/` 是当前工作台最成熟的部分。它正确地把论文当作证据工件，而不是最后一步润色，并已具备官方规则快照、语言控制、图表公式规范、AI 记录、论文角色和 PDF 预检。

需要改造的不是这一原则，而是三点：

1. 去掉具体历史题和固定三问；
2. 把“国奖语言”改成更中性的“证据校准语言”，避免被误解为官方词典；
3. 用机器可读的官方规则 manifest、claim-to-paper 映射和最终签署把流程闭环。

## 2. 当前优点

- `writing/README.md:7-10` 明确官方规则、样本观察和内部风格分层。
- `writing/OFFICIAL_RULES.md:7-17` 明确当届文件优先于历史快照。
- `writing/NATIONAL_AWARD_LANGUAGE.md:24-40` 对最优、因果、显著和稳定等高风险措辞给出证据边界。
- `writing/FIGURE_TABLE_FORMULA_RULES.md:47-54` 要求结果来自固定工件，并分别规范随机算法、优化和机器学习。
- `writing/QA_CHECKLIST.md` 已覆盖内容、数学、数据、引用、AI、版式和视觉 QA。
- `writing/checks/check_pdf.sh` 是只读预检，能检查文件类型、文本标记、身份 token 和 SHA-256。

## 3. 当前缺口

### [P1] 官方来源分级

`cmathc.org.cn` 是整理站，不能与研创网官方公告和附件同列 A 级。应建立：

```text
A0 研创网/组委会官方公告和附件
A1 承办高校官方通知
B 赛事作者或团队原始材料
C 可追溯镜像
D 未验证来源
```

2025 格式和 AI 规则都有研创网官方附件，应以附件 URL 和哈希为主，镜像仅做检索备份。

### [P1] 2026 详细规则尚未冻结

2026 官方邀请函确认使用《竞赛论文标准文档》并提交 PDF/MD5，但没有公开完整排版细则。因此现有 2025 快照只能是 `HISTORICAL_REFERENCE`，不能是 2026 `ACTIVE`。

### [P2] 固定三问和具体题型

`PAPER_STYLE_GUIDE.md`、`QA_CHECKLIST.md` 和 `paper_outline.md` 仍假定问题一至三并写入具体题型。目标模板应从 `problem_contract.subproblems[]` 动态生成。

### [P2] 规则重复

字体、匿名、证据措辞和图表规则在多个文档重复。建议为规则设置稳定 ID，例如：

- `OFF-2026-001` 官方规则；
- `LANG-OPT-001` 最优性措辞；
- `LANG-CAUSAL-001` 因果措辞；
- `QA-PDF-001` PDF 检查。

角色提示词只引用规则 ID，不复制全文。

## 4. 目标论文生产线

```text
官方规则冻结
  → problem/subproblem map
  → claim-evidence ledger
  → paper architecture
  → result tables and figures inventory
  → evidence-calibrated drafting
  → mathematical and code consistency review
  → citation and AI audit
  → adversarial paper review
  → official-template assembly
  → PDF deterministic preflight
  → rendered-page visual QA
  → human sign-off and hash freeze
```

论文作者只能消费 `supported` 或 `supported_with_limits` 的 claim。`draft`、`unverified`、`disputed` 和 `rejected` 不能进入摘要强结论。

## 5. 动态论文结构

固定部分：

- 官方封面与摘要页；
- 问题重述和任务合同；
- 总体技术路线；
- 假设与符号；
- 综合评价、局限和参考文献；
- 当届要求的 AI/支撑材料。

动态部分：对 `subproblems[]` 逐项生成：

```text
问题分析
  → 输入与数据处理
  → 模型/统计方法
  → 算法与实现
  → 结果
  → 验证、敏感性与局限
```

运筹优化章节必须包含变量、目标、约束、可行性、求解器/算法状态和最优性边界；数据分析章节必须包含数据粒度、标签/目标、切分、baseline、指标、不确定性和泄漏控制；Hybrid 章节必须包含接口合同和不确定性传播。

## 6. “国奖语言”的固定方式

建议把文件改名为 `EVIDENCE_CALIBRATED_LANGUAGE.md`，保留以下原则：

| 主张 | 必需证据 | 默认安全表述 |
|---|---|---|
| 可行性 | 独立约束检查 | “得到满足所列约束的可行解” |
| 全局最优 | 证明或有效证书 | “求解器在该模型和容差下返回最优证书” |
| 启发式改进 | baseline、重复实验 | “当前算例/配置下优于基线” |
| 统计显著 | 检验、效应量、样本 | “差异在指定检验下显著，效应量为……” |
| 稳定 | 多种子/折次/扰动 | “在……范围内波动为……” |
| 相关 | 数据和模型 | “呈关联/具有预测贡献” |
| 因果 | 明确识别设计 | “在……识别假设下估计因果效应” |
| 泛化 | 留出/外部验证 | “在指定验证集上观察到” |

摘要中的每个数字都必须绑定 `claim_id + result_artifact_hash + table/figure locator`。

## 7. 官方规则 manifest

建议格式：

```yaml
competition: "Huawei Cup Graduate Mathematical Contest in Modeling"
year: 2026
status: "PENDING | ACTIVE | SUPERSEDED"
retrieved_at: ""
sources:
  - authority: "A0"
    title: ""
    url: ""
    published_at: ""
    local_path: ""
    sha256: ""
rules:
  template: ""
  paper_format: "PDF"
  naming: ""
  anonymity: ""
  abstract_limit: ""
  ai_disclosure: ""
  attachment_limit: ""
  md5_window: ""
```

字段未知时必须为空并标记 `PENDING`，不能从 2025 自动继承。

## 8. 确定性论文检查

在现有 `check_pdf.sh` 之上增加：

- 官方模板/页数/页面尺寸 manifest 比对；
- PDF 元数据和嵌入附件检查；
- 图、表、公式编号与正文引用一致性；
- 摘要数字与结果表一致性；
- 引用编号、参考文献顺序和 URL 检查；
- 身份 token、学校名、作者名和队号检查；
- 占位符、`TODO`、`unverified` 和失效引用检查；
- 最终 PDF hash 与 human signoff 比对。

自动检查只能给出证据和 warning；公式断裂、字体替换、图表裁切、分页和整体可读性仍需渲染后人工逐页检查。

## 9. AI 合规

现有 2025 规则记录方向正确，但每届必须重新冻结。建议每条核心 AI 交互至少记录：

- 工具、实际模型/版本、开发机构和日期；
- 用途、输入摘要和输出摘要；
- 采纳、修改或拒绝；
- 公式、代码、数据和引用的人工核验；
- 对应 artifact/claim/run；
- 不应记录的凭证和敏感信息已移除。

AI 日志证明“如何使用”，不能证明模型、公式或实验本身正确。

## 10. 官方来源

- [2026 研创网参赛邀请函](https://cpipc.acge.org.cn/cw/contestNews/detail/4/2c9080189dcfa24e019dddacc24a1314?page=0)
- [2025 研创网开赛公告及官方附件](https://cpipc.acge.org.cn/cw/contestNews/detail/4/2c90801b9914a68201994b1403512e96?page=1)
- [2025 官方 AI 规定附件](https://cpipc.acge.org.cn/sysFile/downFile.do?fileId=e3edba52b87c4bf7922f737c35c14b74)

## 11. 论文系统验收

- 官方规则来源、状态和哈希明确；
- 章节由题意合同动态生成；
- 论文句子可以追溯到 claim；
- 优化与数据分析的结果语言分别受专业规则约束；
- 引用、AI、数字和图表有独立审查；
- 最终 PDF 通过文本、元数据、渲染和人工签署；
- 签署与提交文件为同一哈希。

