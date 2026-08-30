PAPER_DIR := paper
PAPER_BUILD := $(PAPER_DIR)/build
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

paper-ci: paper
	$(PYTHON) scripts/qa_latex.py --paper-dir $(PAPER_DIR) --build-dir $(PAPER_BUILD)

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
	rm -rf $(PAPER_BUILD)
