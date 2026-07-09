const SITE_TITLE = "\u4e2a\u4eba\u535a\u5ba2";
const LABEL_UNMARKED = "\u672a\u6ce8\u660e";
const LABEL_POSTS = "\u6587\u7ae0\u5f52\u6863";
const LABEL_NO_MATCH = "\u6ca1\u6709\u627e\u5230\u5339\u914d\u7684\u6587\u7ae0\u3002";
const LABEL_POSTS_FAILED = "\u6587\u7ae0\u5217\u8868\u52a0\u8f7d\u5931\u8d25\uff1a";
const LABEL_POST_NOT_FOUND = "\u6ca1\u6709\u627e\u5230\u6587\u7ae0\u6807\u8bc6\u3002";
const LABEL_ARTICLE_FAILED = "\u52a0\u8f7d\u6587\u7ae0\u5931\u8d25\uff1a";
const LABEL_PUBLISHED = "\u53d1\u5e03\u4e8e";
const LABEL_MARKDOWN = "Markdown";

const state = {
  page: document.body.dataset.page || "home",
  articles: [],
  query: "",
  activeSlug: "",
};

function $(id) {
  return document.getElementById(id);
}

function escapeHtml(value) {
  return String(value || "").replace(/[&<>"']/g, (ch) => {
    switch (ch) {
      case "&":
        return "&amp;";
      case "<":
        return "&lt;";
      case ">":
        return "&gt;";
      case '"':
        return "&quot;";
      case "'":
        return "&#39;";
      default:
        return ch;
    }
  });
}

function sortArticles(items) {
  return [...items].sort((a, b) => {
    const dateCompare = (b.date || "").localeCompare(a.date || "");
    if (dateCompare !== 0) {
      return dateCompare;
    }
    return a.title.localeCompare(b.title, "zh-Hans-CN");
  });
}

function filterArticles(items, query) {
  const q = query.trim().toLowerCase();
  if (!q) {
    return [...items];
  }
  return items.filter((article) => {
    const haystack = [article.title, article.summary, article.date].join(" ").toLowerCase();
    return haystack.includes(q);
  });
}

function groupArticles(items) {
  const groups = new Map();

  items.forEach((article) => {
    const key = article.date ? article.date.slice(0, 4) : LABEL_UNMARKED;
    if (!groups.has(key)) {
      groups.set(key, []);
    }
    groups.get(key).push(article);
  });

  const entries = Array.from(groups.entries());
  entries.sort((a, b) => {
    if (a[0] === LABEL_UNMARKED) {
      return 1;
    }
    if (b[0] === LABEL_UNMARKED) {
      return -1;
    }
    return Number(b[0]) - Number(a[0]);
  });

  return entries.map(([year, list]) => [year, sortArticles(list)]);
}

function renderSidebar() {
  const host = $("sidebarContent");
  const count = $("articleCount");
  if (!host || !count) {
    return;
  }

  const filtered = filterArticles(state.articles, state.query);
  count.textContent = state.query ? `${filtered.length} / ${state.articles.length} \u7bc7` : `${state.articles.length} \u7bc7`;

  if (!filtered.length) {
    host.innerHTML = `<div class="empty-state">${LABEL_NO_MATCH}</div>`;
    return;
  }

  host.innerHTML = groupArticles(filtered)
    .map(([year, items]) => {
      const links = items
        .map((article) => {
          const active = article.slug === state.activeSlug ? ' class="active" aria-current="page"' : "";
          return `<li><a${active} href="./article.html?slug=${encodeURIComponent(article.slug)}">${escapeHtml(article.title)}</a></li>`;
        })
        .join("");

      return `
        <section class="sidebar-section">
          <div class="sidebar-section-title">
            <strong>${escapeHtml(year)}</strong>
            <span>${items.length}</span>
          </div>
          <ul class="sidebar-list">${links}</ul>
        </section>
      `;
    })
    .join("");
}

function renderFeed() {
  const host = $("recentPosts");
  if (!host) {
    return;
  }

  const filtered = filterArticles(state.articles, state.query);
  const list = state.query ? filtered : filtered.slice(0, 8);

  if (!list.length) {
    host.innerHTML = `<div class="empty-state">${LABEL_NO_MATCH}</div>`;
    return;
  }

  host.innerHTML = list
    .map((article) => {
      const summary = article.summary ? `<p class="feed-summary">${escapeHtml(article.summary)}</p>` : "";
      return `
        <article class="feed-item">
          <div class="feed-meta">
            <span>${escapeHtml(article.date || LABEL_UNMARKED)}</span>
          </div>
          <div class="feed-title">
            <a href="./article.html?slug=${encodeURIComponent(article.slug)}">${escapeHtml(article.title)}</a>
          </div>
          ${summary}
        </article>
      `;
    })
    .join("");
}

function buildToc() {
  const toc = $("pageToc");
  const tocBox = $("toc");
  if (!toc || !tocBox) {
    return;
  }

  const headings = Array.from(document.querySelectorAll(".content h2, .content h3"));
  const items = headings.filter((heading) => heading.id);

  if (!items.length) {
    toc.innerHTML = "";
    tocBox.hidden = true;
    return;
  }

  tocBox.hidden = false;
  toc.innerHTML = `
    <ul class="toc-list">
      ${items
        .map((heading) => {
          const levelClass = heading.tagName.toLowerCase() === "h3" ? "toc-level-3" : "";
          return `<li class="${levelClass}"><a href="#${escapeHtml(heading.id)}">${escapeHtml(heading.textContent || "")}</a></li>`;
        })
        .join("")}
    </ul>
  `;
}

function renderHome() {
  renderSidebar();
  renderFeed();
  buildToc();
}

function renderArticle(article) {
  state.activeSlug = article.slug;

  const title = $("articleTitle");
  const meta = $("articleMeta");
  const summary = $("articleSummary");
  const body = $("articleBody");

  if (title) {
    title.textContent = article.title;
  }
  if (meta) {
    meta.innerHTML = `
      <span>${LABEL_PUBLISHED} ${escapeHtml(article.date || LABEL_UNMARKED)}</span>
      <span>${LABEL_MARKDOWN}</span>
    `;
  }
  if (summary) {
    if (article.summary) {
      summary.hidden = false;
      summary.textContent = article.summary;
    } else {
      summary.hidden = true;
      summary.textContent = "";
    }
  }
  if (body) {
    body.innerHTML = article.content_html || "<p>\u6682\u65e0\u5185\u5bb9\u3002</p>";
  }

  document.title = `${article.title} - ${SITE_TITLE}`;
  renderSidebar();
  buildToc();
}

async function fetchJson(url) {
  const response = await fetch(`${url}?v=${Date.now()}`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return response.json();
}

function bindSearch() {
  const input = $("searchInput");
  if (!input) {
    return;
  }

  input.addEventListener("input", () => {
    state.query = input.value.trim();
    if (state.page === "home") {
      renderHome();
    } else {
      renderSidebar();
    }
  });
}

async function initHome() {
  document.title = SITE_TITLE;
  renderHome();
}

async function initArticle() {
  const params = new URLSearchParams(window.location.search);
  const slug = params.get("slug");
  const body = $("articleBody");

  if (!slug) {
    if (body) {
      body.innerHTML = `<p>${LABEL_POST_NOT_FOUND}</p>`;
    }
    buildToc();
    return;
  }

  state.activeSlug = slug;
  renderSidebar();

  try {
    const article = await fetchJson(`./articles/${encodeURIComponent(slug)}.json`);
    renderArticle(article);
  } catch (error) {
    if (body) {
      body.innerHTML = `<p>${LABEL_ARTICLE_FAILED}${escapeHtml(error.message)}</p>`;
    }
    buildToc();
  }
}

async function start() {
  try {
    state.articles = sortArticles(await fetchJson("./articles.json"));
  } catch (error) {
    const fallback = $("sidebarContent");
    if (fallback) {
      fallback.innerHTML = `<div class="empty-state">${LABEL_POSTS_FAILED}${escapeHtml(error.message)}</div>`;
    }
    return;
  }

  bindSearch();

  if (state.page === "article") {
    await initArticle();
  } else {
    await initHome();
  }
}

document.addEventListener("DOMContentLoaded", start);
