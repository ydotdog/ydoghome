#!/usr/bin/env python3
"""将 Markdown 文章生成静态 HTML 站点。"""
from __future__ import annotations

import argparse
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional
from urllib.parse import urljoin

import frontmatter
import markdown
import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

DATE_FORMAT = "%Y-%m-%d"
DEFAULT_SRC = "content"
DEFAULT_OUT = "site"
DEFAULT_CONFIG = "config.yml"


@dataclass
class Post:
    title: str
    slug: str
    date: datetime
    updated: Optional[datetime]
    content: str
    excerpt: str

    @property
    def date_iso(self) -> str:
        return self.date.strftime("%Y-%m-%d")

    @property
    def updated_iso(self) -> Optional[str]:
        return self.updated.strftime("%Y-%m-%d") if self.updated else None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate static site from Markdown posts")
    parser.add_argument("--src", default=DEFAULT_SRC, help="Source directory containing Markdown content")
    parser.add_argument("--out", default=DEFAULT_OUT, help="Output directory for the generated site")
    parser.add_argument("--config", default=DEFAULT_CONFIG, help="Path to YAML configuration file")
    return parser.parse_args()


def resolve_path(path_str: str, project_root: Path) -> Path:
    path = Path(path_str)
    if path.is_absolute():
        return path
    return project_root / path


def read_config(config_path: Path) -> dict:
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with config_path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    return data


def load_posts(src_dir: Path) -> List[Post]:
    posts_dir = src_dir / "posts"
    if not posts_dir.exists():
        return []

    posts: List[Post] = []
    md = markdown.Markdown(extensions=["extra", "toc", "sane_lists"])

    for path in sorted(posts_dir.rglob("*.md")):
        post_data = frontmatter.load(path)
        meta = post_data.metadata

        if meta.get("draft", False):
            continue

        title = meta.get("title") or path.stem
        raw_date = meta.get("date")
        if not raw_date:
            raise ValueError(f"Missing 'date' in front matter: {path}")
        date = datetime.strptime(str(raw_date), DATE_FORMAT)

        updated_value = meta.get("updated")
        updated = None
        if updated_value:
            updated = datetime.strptime(str(updated_value), DATE_FORMAT)

        slug = meta.get("slug") or path.stem

        # Reset markdown instance to avoid state bleed (e.g., TOC)
        md.reset()
        html_content = md.convert(post_data.content)

        excerpt = build_excerpt(post_data.content)

        posts.append(
            Post(
                title=title,
                slug=slug,
                date=date,
                updated=updated,
                content=html_content,
                excerpt=excerpt,
            )
        )

    posts.sort(key=lambda p: p.date, reverse=True)
    return posts


def build_excerpt(text: str, length: int = 140) -> str:
    plain = " ".join(line.strip() for line in text.splitlines())
    plain = " ".join(plain.split())
    if len(plain) <= length:
        return plain
    return plain[: length - 1].rstrip() + "…"


def prepare_environment(templates_dir: Path) -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    return env


def ensure_empty_directory(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def copy_assets(src: Path, dst: Path) -> None:
    assets_src = src / "assets"
    if assets_src.exists():
        shutil.copytree(assets_src, dst / "assets")


def write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        fh.write(content)


def generate_posts(env: Environment, posts: Iterable[Post], out_dir: Path, site_meta: dict) -> List[str]:
    template = env.get_template("post.html")
    urls: List[str] = []
    for post in posts:
        html = template.render(post=post, site_title=site_meta["site_title"], site_description=site_meta.get("site_description"))
        out_path = out_dir / "posts" / f"{post.slug}.html"
        write_file(out_path, html)
        urls.append(f"/posts/{post.slug}.html")
    return urls


def generate_index(env: Environment, posts: Iterable[Post], out_dir: Path, site_meta: dict) -> str:
    template = env.get_template("index.html")
    html = template.render(posts=posts, site_title=site_meta["site_title"], site_description=site_meta.get("site_description"))
    write_file(out_dir / "index.html", html)
    return "/"


def generate_sitemap(out_dir: Path, base_url: str, routes: Iterable[str]) -> None:
    base = base_url.rstrip("/") + "/"
    items = [urljoin(base, route.lstrip("/")) for route in routes]
    lines = [
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>",
        "<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">",
    ]
    for loc in items:
        lines.extend([
            "  <url>",
            f"    <loc>{loc}</loc>",
            "  </url>",
        ])
    lines.append("</urlset>")
    write_file(out_dir / "sitemap.xml", "\n".join(lines) + "\n")


def generate_robots(out_dir: Path, base_url: str) -> None:
    lines = [
        "User-agent: *",
        "Allow: /",
        f"Sitemap: {base_url.rstrip('/')}/sitemap.xml",
        "",
    ]
    write_file(out_dir / "robots.txt", "\n".join(lines))


def generate_headers(out_dir: Path) -> None:
    content = "\n".join(
        [
            "/*",
            "  Cache-Control: no-cache",
            "",
            "/assets/*",
            "  Cache-Control: public, max-age=31536000, immutable",
            "",
        ]
    )
    write_file(out_dir / "_headers", content)


def main() -> None:
    args = parse_args()

    project_root = Path(__file__).resolve().parent.parent

    src_dir = resolve_path(args.src, project_root)
    out_dir = resolve_path(args.out, project_root)
    config_path = resolve_path(args.config, project_root)

    config = read_config(config_path)
    site_title = config.get("site_title", "My Blog")
    base_url = config.get("base_url", "")
    site_description = config.get("site_description")

    ensure_empty_directory(out_dir)

    posts = load_posts(src_dir)
    env = prepare_environment(project_root / "templates")

    site_meta = {
        "site_title": site_title,
        "site_description": site_description,
    }

    routes: List[str] = []
    routes.append(generate_index(env, posts, out_dir, site_meta))
    routes.extend(generate_posts(env, posts, out_dir, site_meta))

    copy_assets(project_root, out_dir)

    if base_url:
        generate_sitemap(out_dir, base_url, routes)
        generate_robots(out_dir, base_url)
    else:
        # still produce empty placeholders to avoid missing files
        generate_sitemap(out_dir, "https://example.com", routes)
        generate_robots(out_dir, "https://example.com")

    generate_headers(out_dir)


if __name__ == "__main__":
    main()
