.PHONY: build install uninstall clean

build:
	bash scripts/build.sh

install: build
	mkdir -p ~/.local/share/fonts
	cp dist/fingertap-icons.ttf ~/.local/share/fonts/
	fc-cache -fv

uninstall:
	rm -f ~/.local/share/fonts/fingertap-icons.ttf
	fc-cache -fv

clean:
	rm -rf dist/* icons/svg/*
