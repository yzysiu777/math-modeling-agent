"""Warn when workbench guidance has absorbed the vocabulary of one problem.

The workbench serves a class of problems, not the problem currently on the desk.
That line has been crossed twice: once with a gate's justification written in the
terms of a specific dataset, once with a protocol using a domain-specific claim
as its counter-example. Both times a human found it by grepping, and a human
forgets to grep.

The check runs backwards from the case rather than from a hard-coded word list --
a hard-coded list would itself be fitted to one problem. It takes the terms that
recur in this case's own statement and asks whether any of them turned up in the
workbench's rules.

False positives are expected and intended: the output is a prompt to go look,
never a verdict. Nothing here blocks.
"""

from __future__ import annotations

import argparse
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GUIDANCE_DIRS = ("protocol", "prompts", "docs", ".agents", "writing", "templates")
GUIDANCE_ROOT_FILES = ("README.md", "AGENTS.md", "agent.md", "REVIEWER.md")
CHINESE_RUN = re.compile(r"[一-鿿]{2,}")
MIN_TERM = 3
MIN_COUNT = 3

#: 虚词。以它开头或结尾的都是跨词边界的碎片（「的结果」「个文件」），不是术语。
EDGE_FUNCTION_CHARS = set("的是个在和与每有了也就都及或而但其之为以对从到中上下内外前后这那要能可将被把")

#: 通用建模与数据词。与题目无关，换任何一道题这份表都不变。
STOPWORDS = {
    "模型", "数据", "分析", "问题", "结果", "方法", "计算", "误差", "参数", "变量",
    "指标", "评价", "验证", "检验", "假设", "约束", "目标", "优化", "求解", "算法",
    "实验", "样本", "统计", "时间", "空间", "范围", "条件", "过程", "特征", "信息",
    "系统", "研究", "建立", "给出", "要求", "考虑", "本题", "附件", "题目", "以及",
    "可以", "需要", "进行", "通过", "根据", "对于", "如下", "包括", "其中", "不同",
    "相关", "影响", "变化", "关系", "情况", "问题一", "问题二", "问题三", "第一题",
    "第二题", "第三题", "数据分析", "数学建模",
    "数据文件", "文件名", "数据格式", "格式说明", "版本号", "分辨率", "采样",
    "观测", "记录", "字段", "单位", "高度", "位置", "坐标", "站点", "设备",
}


def _maximal_terms(text: str) -> Counter:
    """Repeated Chinese terms, longest form only."""

    counts: Counter = Counter()
    for run in CHINESE_RUN.findall(text):
        for size in range(MIN_TERM, min(len(run), 8) + 1):
            for start in range(len(run) - size + 1):
                counts[run[start:start + size]] += 1
    frequent = {term: n for term, n in counts.items() if n >= MIN_COUNT}
    # 丢掉被更长同频词包含的片段，留下最长形式。
    return Counter({
        term: n for term, n in frequent.items()
        if not any(term != other and term in other and frequent[other] >= n
                   for other in frequent)
    })


def case_terms(case_dir: Path) -> Counter:
    sources = [case_dir / "input/题面全文.md"]
    docs = case_dir / "input/说明文档"
    if docs.is_dir():
        sources.extend(sorted(docs.glob("*.md")))
    text = "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in sources if path.is_file()
    )
    terms = _maximal_terms(text)
    for word in STOPWORDS:
        terms.pop(word, None)
    return Counter({
        term: n for term, n in terms.items()
        if term[0] not in EDGE_FUNCTION_CHARS and term[-1] not in EDGE_FUNCTION_CHARS
        and not any(word in term for word in STOPWORDS)
    })


def guidance_files() -> list[Path]:
    found = [ROOT / name for name in GUIDANCE_ROOT_FILES]
    for directory in GUIDANCE_DIRS:
        found.extend(sorted((ROOT / directory).rglob("*.md")))
    return [path for path in found if path.is_file()]


def find_leaks(case_dir: Path) -> list[str]:
    terms = case_terms(case_dir)
    if not terms:
        return []
    leaks: list[str] = []
    for path in guidance_files():
        text = path.read_text(encoding="utf-8", errors="ignore")
        relative = path.relative_to(ROOT).as_posix()
        for term, _ in terms.most_common():
            if term in text:
                leaks.append(
                    f"{relative}: 出现了本案例题面的词「{term}」—— "
                    "确认这是通用规则，还是把这道题写进了工作台"
                )
    return leaks


def main() -> int:
    parser = argparse.ArgumentParser(description="warn about problem-specific vocabulary")
    parser.add_argument("--case-dir", type=Path, required=True)
    args = parser.parse_args()
    if not (args.case_dir / "input/题面全文.md").is_file():
        print(f"SKIP overfit check: 案例还没有阶段 0 的题面全文：{args.case_dir}")
        return 0
    leaks = find_leaks(args.case_dir)
    if not leaks:
        print("OK 工作台规范里没有出现本案例题面的专有词")
        return 0
    print(f"REMINDER 工作台规范疑似吸收了本案例的词汇（{len(leaks)} 处，不阻断）")
    print("\n".join(f"- {item}" for item in leaks))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
