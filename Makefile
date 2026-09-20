UNAME := $(shell uname -s)

.PHONY: build install uninstall clean deps

deps:
ifeq ($(UNAME),Darwin)
	brew install fontforge potrace imagemagick
else ifeq ($(shell command -v pacman 2>/dev/null),)
	sudo apt-get install -y fontforge python3-fontforge potrace imagemagick
else
	sudo pacman -S --needed --noconfirm fontforge potrace imagemagick
endif

build:
	@command -v fontforge >/dev/null 2>&1 || { echo "Error: fontforge not found. Run 'make deps' first."; exit 1; }
	bash scripts/build.sh

install: build
ifeq ($(UNAME),Darwin)
	cp dist/fingertap-icons.ttf ~/Library/Fonts/
else
	mkdir -p ~/.local/share/fonts
	cp dist/fingertap-icons.ttf ~/.local/share/fonts/
	fc-cache -fv
endif
	@# Publish the name -> codepoint mapping so consumers (polybar, waybar,
	@# scripts) can resolve icons by name instead of hardcoding characters.
	mkdir -p ~/.local/share/fingertap-icons
	cp dist/codepoints.json ~/.local/share/fingertap-icons/codepoints.json
	@echo "Mapping published: ~/.local/share/fingertap-icons/codepoints.json"

uninstall:
ifeq ($(UNAME),Darwin)
	rm -f ~/Library/Fonts/fingertap-icons.ttf
else
	rm -f ~/.local/share/fonts/fingertap-icons.ttf
	fc-cache -fv
endif
	rm -rf ~/.local/share/fingertap-icons

clean:
	rm -rf dist/* icons/svg/*
