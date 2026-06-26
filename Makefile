.PHONY: bundle

bundle:
	{ git ls-files; git ls-files --others --exclude-standard; } | zip -@ python-shiny-masterclass.zip
	@echo "Created python-shiny-masterclass.zip"
