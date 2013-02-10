name=wsj_comp
latex=/usr/texbin/latex
dvips=/usr/texbin/dvips

tex: $(name).tex
	$(latex) $(name)
	$(latex) $(name)
	$(dvips) $(name).dvi
	ps2pdf $(name).ps

clean:
	rm *aux *log *pdf *ps *dvi
