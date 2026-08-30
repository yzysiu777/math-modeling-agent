PAPER_DIR := paper
PAPER_BUILD := $(PAPER_DIR)/build
PAPER_EXAMPLE_BUILD := $(PAPER_DIR)/upstream/build
PYTHON ?= python3

# gmcmthesis 默认用本机中文字体（Mac: SimSun/STSong，Windows: SimSun）。
# CI 与 Linux 上这些字体不存在，需要 ctex 的 fandol 字体集。
# 设 PAPER_FONTSET=fandol 即可注入；本机留空使用系统字体，排版更接近提交稿。
PAPER_FONTSET ?=
ifneq ($(PAPER_FONTSET),)
LATEXMK_PRETEX := -usepretex='\PassOptionsToClass{fontset=$(PAPER_FONTSET)}{ctexart}'
endif

.PHONY: paper paper-ci qa clean test validate demos case-check spec-check review-packet final-check

paper:
	mkdir -p $(PAPER_BUILD)
	cd $(PAPER_DIR) && latexmk -r ../latexmkrc -xelatex $(LATEXMK_PRETEX) -interaction=nonstopmode -halt-on-error -outdir=build main.tex

# 编译上游示例，展示这套模板支持的排版元素（算法、表格、子图、代码附录）。
# 与论文工程完全隔离：不同的源、不同的构建目录，不会污染 paper/build。
# 它同时是一道回归——换 2026 版模板时，这里编不过说明上游有破坏性变更。
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

case-check:
	@test -n "$(CASE)" || (echo "CASE is required"; exit 2)
	@test -n "$(STAGE)" || (echo "STAGE is required"; exit 2)
	$(PYTHON) scripts/check_case.py --case-dir "$(CASE)" --stage "$(STAGE)"

spec-check:
	@test -n "$(CASE)" || (echo "CASE is required"; exit 2)
	$(PYTHON) scripts/check_spec.py --case-dir "$(CASE)"

review-packet:
	@test -n "$(CASE)" || (echo "CASE is required"; exit 2)
	@test -n "$(NODE)" || (echo "NODE is required (C1, C2 or C3)"; exit 2)
	$(PYTHON) scripts/make_review_packet.py --case-dir "$(CASE)" --node "$(NODE)"

final-check:
	@test -n "$(CASE)" || (echo "CASE is required"; exit 2)
	@status=0; \
	$(PYTHON) scripts/check_case.py --case-dir "$(CASE)" --stage final || status=$$?; \
	$(PYTHON) scripts/check_spec.py --case-dir "$(CASE)" || status=$$?; \
	$(MAKE) PYTHON="$(PYTHON)" paper-ci || status=$$?; \
	if [ -f $(PAPER_BUILD)/main.pdf ]; then sh writing/checks/check_pdf.sh $(PAPER_BUILD)/main.pdf || status=$$?; fi; \
	exit $$status

clean:
	cd $(PAPER_DIR) && latexmk -r ../latexmkrc -C -outdir=build main.tex || true
	rm -rf $(PAPER_BUILD) $(PAPER_EXAMPLE_BUILD)
