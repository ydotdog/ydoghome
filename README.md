# Markdown 静态博客脚手架

这是一个使用 Python 3.11+ 构建的极简静态站点生成器示例。它会将 `content/posts/*.md` 转换为 HTML，并生成适用于 Cloudflare Pages 的产物。

## 功能特性

- 解析 Markdown 文件与 YAML Front Matter（title/date/updated/slug/draft）。
- 根据日期倒序生成首页及文章详情页。
- 忽略 `draft: true` 的文章。
- 自动复制静态资源、生成 `sitemap.xml` 与 `robots.txt`。
- 输出 `_headers`，配置 HTML 不缓存、静态资源长缓存。

## 快速开始

### 环境准备

1. 安装 Python 3.11 及以上版本。
2. （可选）创建虚拟环境：
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
3. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```

### 本地构建与预览

```bash
make build      # 生成 site/ 静态文件
make preview    # 在 http://localhost:8000 预览
```

`make preview` 会先执行构建，再通过内置 HTTP 服务器提供静态页面。修改 `content/posts/*.md` 后重新运行 `make build` 即可刷新输出。

## 目录结构

```
your-blog/
├── assets/              # 静态资源（会被复制到 site/assets/）
├── config.yml           # 站点配置，包含 base_url 与 site_title
├── content/posts/       # Markdown 文章（含 YAML Front Matter）
├── scripts/generate_site.py  # 构建脚本
├── templates/           # Jinja2 模板：base、post、index
├── site/                # 构建输出目录（git 已忽略）
└── ...
```

## Cloudflare Pages 配置

- **Build command**：`make build`
- **Build output directory**：`site`
- **Environment**：Python 3.11（可在 Pages 设置中指定）

部署完成后，`_headers` 文件会确保：

- 所有 HTML：`Cache-Control: no-cache`
- 静态资源 `/assets/*`：`Cache-Control: public, max-age=31536000, immutable`

## 常见问题

### 如何新增文章？
在 `content/posts/` 下新增 `.md` 文件，包含以下 Front Matter 字段：
```yaml
---
title: 新文章标题
date: 2024-06-10
updated: 2024-06-10
slug: new-post-slug
draft: false
---
```
执行 `make build` 后即可生成对应的 HTML 页面。

### Front Matter 中的日期格式是什么？
使用 `YYYY-MM-DD`，例如 `2024-06-01`。如格式不正确，脚本会抛出错误。

### 可以隐藏草稿吗？
将 Front Matter 中的 `draft` 设置为 `true`，构建时会自动跳过该文章。

### 如何清理构建产物？
执行：
```bash
make clean
```
这会删除 `site/` 目录。

