PAPER_DIR := paper
PAPER_BUILD := $(PAPER_DIR)/build
PYTHON ?= python3

.PHONY: paper paper-ci qa clean test validate demos

paper:
	mkdir -p $(PAPER_BUILD)
	cd $(PAPER_DIR) && latexmk -r ../latexmkrc -xelatex -interaction=nonstopmode -halt-on-error -outdir=build main.tex

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

clean:
	cd $(PAPER_DIR) && latexmk -r ../latexmkrc -C -outdir=build main.tex || true
	rm -rf $(PAPER_BUILD)
