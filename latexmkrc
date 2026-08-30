# gmcmthesis 需要 XeLaTeX，且用经典 BibTeX + gmcm.bst（不是 biber/biblatex）。
$pdf_mode = 5;
$xelatex = 'xelatex -interaction=nonstopmode -halt-on-error %O %S';
$bibtex = 'bibtex %O %B';
$bibtex_use = 2;
$max_repeat = 5;
# 让 bibtex 在 -outdir 下也能找到 bibliography/references.bib
$ENV{'BIBINPUTS'} = './bibliography:' . ($ENV{'BIBINPUTS'} // '');
