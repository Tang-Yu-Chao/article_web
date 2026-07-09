# ArticleWeb

一个很轻的个人博客站点。

## 用法

把 Markdown 文章放进 `quotes/`（或新建 `posts/`），然后运行：

```bash
python build.py
```

脚本会生成：

- `articles.json`：文章列表
- `articles/*.json`：每篇文章的页面数据

首页是 `index.html`，文章页是 `article.html?slug=文章文件名`。

## 发布

仓库已配置 GitHub Pages 工作流，推送后会自动构建并发布。
