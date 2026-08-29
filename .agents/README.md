# Codex 仓库级扩展

Codex 从 `.agents/skills/` 自动发现本仓库的 Skill。三个 Skill 与三个角色一一对应：

| Skill | 角色 | 提示词 |
|---|---|---|
| `competition-modeling` | 建模手 | `prompts/modeler.md` |
| `competition-engineering` | 编程手 | `prompts/engineer.md` |
| `competition-paper-writing` | 写作手 | `prompts/writer.md` |

Skill 的详细方法放在各自 `references/` 中，只有任务需要时才读取。项目长期规则由根
目录 `AGENTS.md` 提供，角色边界和交接契约见 `prompts/`，比赛案例保存在 `cases/`。
三者职责不要混合。

独立审核者（C1/C2/C3）不使用本仓库的 Skill，见 `REVIEWER.md`。
