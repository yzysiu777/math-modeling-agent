PAPER_DIR := paper
PAPER_BUILD := $(PAPER_DIR)/build
PAPER_EXAMPLE_BUILD := $(PAPER_DIR)/upstream/build
# 默认用工作台虚拟环境。检查器依赖 PyYAML，用系统 python 跑会读不出 checkpoint，
# 于是绝大部分检查被跳过 —— 实测中真的发生过，且探索阶段还返回 exit 0。
PYTHON ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)

# gmcmthesis 默认用本机中文字体（Mac: SimSun/STSong，Windows: SimSun）。
# CI 与 Linux 上这些字体不存在，需要 ctex 的 fandol 字体集。
# 设 PAPER_FONTSET=fandol 即可注入；本机留空使用系统字体，排版更接近提交稿。
PAPER_FONTSET ?=
PRETEX :=
ifneq ($(PAPER_FONTSET),)
PRETEX := $(PRETEX)\PassOptionsToClass{fontset=$(PAPER_FONTSET)}{ctexart}
endif
# Q=q1 只编译该题。案例 main.tex 的 \InputQuestion 读 \PaperOnly 决定是否展开。
ifneq ($(Q),)
PRETEX := $(PRETEX)\def\PaperOnly{$(Q)}
QSUFFIX := -$(Q)
endif
ifneq ($(PRETEX),)
LATEXMK_PRETEX := -usepretex='$(PRETEX)'
endif

.PHONY: paper paper-ci qa clean test validate demos ingest case-check spec-check review-packet start-prompt final-check

# 不带 CASE 编译仓库论文工程；带 CASE 编译该案例的论文。
# 案例只放自己的内容，文档类、样式、bst 和封面图经 TEXINPUTS 从仓库 paper/ 解析 ——
# 第三次实测里写作手因为案例没有主文档而自造了一份 ctexart，绕开了官方版式。
paper:
ifeq ($(CASE),)
	mkdir -p $(PAPER_BUILD)
	cd $(PAPER_DIR) && latexmk -r ../latexmkrc -xelatex $(LATEXMK_PRETEX) -interaction=nonstopmode -halt-on-error -outdir=build main.tex
else
	@test -f "$(CASE)/paper/main.tex" || (echo "案例没有论文工程：$(CASE)/paper/main.tex"; exit 2)
	mkdir -p "$(CASE)/output/pdf"
	cd "$(CASE)/paper" && \
	  TEXINPUTS=".:$(CURDIR)/$(PAPER_DIR)//:" BSTINPUTS=".:$(CURDIR)/$(PAPER_DIR):" \
	  latexmk -r "$(CURDIR)/latexmkrc" -xelatex $(LATEXMK_PRETEX) \
	    -interaction=nonstopmode -halt-on-error -outdir=build main.tex
	@name=$$(basename "$(CASE)"); \
	  cp "$(CASE)/paper/build/main.pdf" "$(CASE)/output/pdf/$$name$(QSUFFIX).pdf"; \
	  echo "已编译：$(CASE)/output/pdf/$$name$(QSUFFIX).pdf"
endif

# 编译上游示例，展示这套模板支持的排版元素（算法、表格、子图、代码附录）。
# 与论文工程完全隔离：不同的源、不同的构建目录，不会污染 paper/build。
# 它同时是一道回归——换 2026 版模板时，这里编不过说明上游有破坏性变更。
#
# 只在 macOS / Windows 上能跑：文档类的 Matlab/Python 代码环境在环境内部写死了
# \fontspec{Courier New}，Linux 没有这个字体，且因为写在环境里，外部覆盖无效。
# 修它就要改动按字节收录的 example.tex 或 .cls，会破坏 upstream/README.md 的
# 校验和契约，不值得。因此 CI 不跑这个目标，只跑源完整性测试。
paper-example:
	mkdir -p $(PAPER_EXAMPLE_BUILD)
	cd $(PAPER_DIR)/upstream && \
	  TEXINPUTS=".:..:../figures//:" BSTINPUTS=".:..:" \
	  latexmk -r ../../latexmkrc -xelatex $(LATEXMK_PRETEX) \
	    -interaction=nonstopmode -halt-on-error -outdir=build example.tex
	@echo "上游示例已编译：$(PAPER_EXAMPLE_BUILD)/example.pdf"
	@echo "片段用法见 writing/LATEX_SNIPPETS.md；源码见 $(PAPER_DIR)/upstream/example.tex"

# 抽取 writing/LATEX_SNIPPETS.md 里的片段，用本仓库的文档类和样式实际编译。
# 片段库只靠肉眼看会悄悄烂掉，而人是在比赛压力下复制它们的。
snippet-check:
	$(PYTHON) scripts/check_snippets.py $(if $(PAPER_FONTSET),--fontset $(PAPER_FONTSET),)

paper-ci: paper
	$(PYTHON) scripts/qa_latex.py --paper-dir $(PAPER_DIR) --build-dir $(PAPER_BUILD)
	$(MAKE) PYTHON="$(PYTHON)" PAPER_FONTSET="$(PAPER_FONTSET)" snippet-check

qa:
	$(PYTHON) scripts/qa_latex.py --paper-dir $(PAPER_DIR) --build-dir $(PAPER_BUILD)
	@if [ -f $(PAPER_BUILD)/main.pdf ]; then sh writing/checks/check_pdf.sh $(PAPER_BUILD)/main.pdf; fi

validate:
	$(PYTHON) scripts/validate_workspace.py

test:
	$(PYTHON) -m unittest discover -s tests -v

demos:
	$(PYTHON) scripts/run_demos.py

ingest:
	@test -n "$(CASE)" || (echo "CASE is required"; exit 2)
	$(PYTHON) scripts/ingest.py --case-dir "$(CASE)"

case-check:
	@test -n "$(CASE)" || (echo "CASE is required"; exit 2)
	@test -n "$(STAGE)" || (echo "STAGE is required"; exit 2)
	$(PYTHON) scripts/check_case.py --case-dir "$(CASE)" --stage "$(STAGE)"

spec-check:
	@test -n "$(CASE)" || (echo "CASE is required"; exit 2)
	$(PYTHON) scripts/check_spec.py --case-dir "$(CASE)"

# 从案例生成角色启动提示词。规则在 prompts/，事实在案例里，这里只填空和指路 ——
# 手写提示词会把题目结论抄进去，抄一次就多一处会过期的副本。
start-prompt:
	@test -n "$(CASE)" || (echo "CASE is required"; exit 2)
	@test -n "$(ROLE)" || (echo "ROLE is required (orchestrator/modeler/engineer/writer/reviewer)"; exit 2)
	$(PYTHON) scripts/make_start_prompt.py --case-dir "$(CASE)" --role "$(ROLE)" $(if $(Q),--question $(Q),) $(if $(NODE),--node $(NODE),)

review-packet:
	@test -n "$(CASE)" || (echo "CASE is required"; exit 2)
	@test -n "$(NODE)" || (echo "NODE is required (C1, C2 or C3)"; exit 2)
	$(PYTHON) scripts/make_review_packet.py --case-dir "$(CASE)" --node "$(NODE)" $(if $(QUESTION),--question "$(QUESTION)",)

final-check:
	@test -n "$(CASE)" || (echo "CASE is required"; exit 2)
	@status=0; \
	$(PYTHON) scripts/check_case.py --case-dir "$(CASE)" --stage final || status=$$?; \
	$(PYTHON) scripts/check_spec.py --case-dir "$(CASE)" || status=$$?; \
	$(MAKE) PYTHON="$(PYTHON)" paper-ci || status=$$?; \
	$(PYTHON) scripts/qa_latex.py --paper-dir $(PAPER_DIR) --build-dir $(PAPER_BUILD) --final || status=$$?; \
	if [ -f $(PAPER_BUILD)/main.pdf ]; then sh writing/checks/check_pdf.sh $(PAPER_BUILD)/main.pdf || status=$$?; fi; \
	exit $$status

clean:
	cd $(PAPER_DIR) && latexmk -r ../latexmkrc -C -outdir=build main.tex || true
	rm -rf $(PAPER_BUILD) $(PAPER_EXAMPLE_BUILD)
