.PHONY: build preview deploy clean

build:
python3 scripts/generate_site.py --src content --out site --config config.yml

preview: build
cd site && python3 -m http.server 8000

deploy: build
@echo "部署由 Cloudflare Pages 完成。请在控制台触发发布。"

clean:
rm -rf site
