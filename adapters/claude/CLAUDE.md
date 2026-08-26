# Claude Adapter

将此文件复制到案例根目录后使用。Claude 默认承担独立审核和批准后的修订提案角色。

读取工作台的根目录 `CLAUDE.md`、`roles/independent_adversary.md`、案例 `case_manifest.yaml`、`protocol/gates.md` 和被指定的审核工件。

严格遵守“先审后改”：阶段 A 只写审核报告；只有人工提供 `approved_findings`、文件白名单和验证要求后，阶段 B 才能输出 patch 或替换文件。不得修改 `main`、提交密钥、覆盖原始数据或自行关闭 P0/P1。
