import unittest

from scripts.gate_contract import GATES
from scripts.validate_workspace import extract_gate_rows, validate_gate_mirror, validate_static_contract


def gate_table():
    lines = ["| Gate | 名称 | 进入状态 | 首次通过的退出证据 |", "|---|---|---|---|"]
    lines.extend(f"| {gate.gate_id} | {gate.name} | `{gate.state}` | {gate.exit_evidence} |" for gate in GATES)
    return "\n".join(lines)


class WorkspaceContractTests(unittest.TestCase):
    def test_current_workspace_contract_is_clean(self):
        self.assertEqual(validate_static_contract(), [])

    def test_gate_mirror_rejects_swapped_name_or_state(self):
        text = gate_table()
        self.assertEqual(len(extract_gate_rows(text)), 13)
        broken = text.replace("| G4 | 正式模型和算法 | `model_ready` |", "| G4 | 正确性、可行性与边界 | `model_ready` |")
        self.assertTrue(validate_gate_mirror(broken))


if __name__ == "__main__":
    unittest.main()
