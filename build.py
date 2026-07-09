import html
import json
import re
import shutil
from datetime import datetime
from pathlib import Path

SOURCE_DIRS = [Path("posts"), Path("quotes")]
OUTPUT_LIST = Path("articles.json")
OUTPUT_DIR = Path("articles")

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
UL_RE = re.compile(r"^[-*+]\s+(.*)$")
OL_RE = re.compile(r"^\d+\.\s+(.*)$")
QUOTE_RE = re.compile(r"^>\s?(.*)$")
HR_RE = re.compile(r"^(?:---+|\*\*\*+|___+)$")
CODE_FENCE_RE = re.compile(r"^(```|~~~)(.*)$")


def pick_source_dir():
    for directory in SOURCE_DIRS:
        if directory.exists() and any(directory.glob("*.md")):
            return directory
    raise FileNotFoundError("No markdown files found in posts/ or quotes/.")


def split_front_matter(text):
    if not text.startswith("---\n"):
        return {}, text

    lines = text.splitlines()
    meta_lines = []
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return parse_meta_lines(meta_lines), "\n".join(lines[index + 1 :])
        meta_lines.append(lines[index])
    return {}, text


def parse_meta_lines(lines):
    meta = {}
    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip().lower()
        value = value.strip().strip('"').strip("'")
        if key == "tags":
            meta[key] = [part for part in re.split(r"[,\s/|,，、]+", value) if part]
        else:
            meta[key] = value
    return meta


def parse_date(value):
    if not value:
        return None

    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%Y%m%d"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            pass

    match = re.search(r"(\d{8})", text)
    if match:
        try:
            return datetime.strptime(match.group(1), "%Y%m%d")
        except ValueError:
            return None
    return None


def date_from_stem(stem):
    match = re.search(r"(\d{8})", stem)
    if not match:
        return None
    try:
        return datetime.strptime(match.group(1), "%Y%m%d")
    except ValueError:
        return None


def date_to_string(value):
    return value.strftime("%Y-%m-%d") if value else ""


def normalize_text(text):
    return re.sub(r"\s+", "", text or "").lower()


def humanize_stem(stem):
    cleaned = re.sub(r"^\d+_\d+\.\d{8}", "", stem)
    cleaned = re.sub(r"^\d+_\d+\.\d{4}[-_.]\d{2}[-_.]\d{2}", "", cleaned)
    cleaned = re.sub(r"^\d{8}", "", cleaned)
    cleaned = cleaned.strip("._- ")
    return cleaned or stem


def extract_title(body, meta, stem):
    if meta.get("title"):
        return str(meta["title"]).strip()

    for raw_line in body.splitlines():
        match = HEADING_RE.match(raw_line.strip())
        if match:
            return match.group(2).strip()

    return humanize_stem(stem)


def remove_leading_title_block(body, title, stem):
    lines = body.splitlines()
    result = []
    skipped_first_heading = False
    skipped_title_line = False
    candidates = {normalize_text(title), normalize_text(humanize_stem(stem))}

    for raw_line in lines:
        stripped = raw_line.strip()
        if not skipped_first_heading and stripped.startswith("# "):
            skipped_first_heading = True
            continue
        if skipped_first_heading and not skipped_title_line and stripped and normalize_text(stripped) in candidates:
            skipped_title_line = True
            continue
        result.append(raw_line)

    return "\n".join(result).strip("\n")


def strip_inline_markdown(text):
    text = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"__([^_]+)__", r"\1", text)
    text = re.sub(r"[*_]", "", text)
    return text


def looks_like_heading(text):
    stripped = text.strip()
    if not stripped or len(stripped) > 40:
        return False
    if re.search(r"[。！？!?；;，,]", stripped):
        return False
    return True


def extract_summary(body, title, stem):
    chunks = []
    candidate_text = body.splitlines()
    title_candidates = {normalize_text(title), normalize_text(humanize_stem(stem))}

    for raw_line in candidate_text:
        line = raw_line.strip()
        if not line:
            if chunks:
                break
            continue
        if line.startswith("#"):
            continue
        if normalize_text(line) in title_candidates:
            continue
        if line.startswith("["):
            continue

        plain = re.sub(r"\s+", " ", strip_inline_markdown(line)).strip()
        if plain:
            chunks.append(plain)
        if len(" ".join(chunks)) >= 180:
            break

    summary = re.sub(r"\s+", " ", " ".join(chunks)).strip()
    if len(summary) > 140:
        summary = summary[:137].rstrip() + "..."
    return summary


def render_inline(text):
    code_spans = []

    def hide_code(match):
        code_spans.append(html.escape(match.group(1), quote=False))
        return "\u0000{}\u0000".format(len(code_spans) - 1)

    text = re.sub(r"`([^`]+)`", hide_code, text)
    text = html.escape(text, quote=False)
    text = re.sub(
        r"!\[([^\]]*)\]\(([^)]+)\)",
        lambda match: '<img alt="{0}" src="{1}">'.format(
            html.escape(match.group(1), quote=True),
            html.escape(match.group(2), quote=True),
        ),
        text,
    )
    text = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        lambda match: '<a href="{0}" target="_blank" rel="noreferrer noopener">{1}</a>'.format(
            html.escape(match.group(2), quote=True),
            match.group(1),
        ),
        text,
    )
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"__([^_]+)__", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*([^*<]+?)\*(?!\*)", r"<em>\1</em>", text)
    text = re.sub(r"(?<!_)_([^_<]+?)_(?!_)", r"<em>\1</em>", text)

    def restore_code(match):
        return "<code>{}</code>".format(code_spans[int(match.group(1))])

    return re.sub(r"\u0000(\d+)\u0000", restore_code, text)


def slugify_heading(text, used_ids, index):
    base = re.sub(r"<[^>]+>", "", text)
    base = re.sub(r"[^\w\u4e00-\u9fff-]+", "-", base, flags=re.UNICODE)
    base = base.strip("-").lower()
    if not base:
        base = "section-{}".format(index)

    candidate = base
    suffix = 2
    while candidate in used_ids:
        candidate = "{}-{}".format(base, suffix)
        suffix += 1

    used_ids.add(candidate)
    return candidate


def markdown_to_html(text):
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    blocks = []
    paragraph = []
    quote = []
    list_items = []
    list_type = None
    in_code = False
    code_lang = ""
    code_lines = []

    def flush_paragraph():
        nonlocal paragraph
        if paragraph:
            text = " ".join(paragraph).strip()
            if len(paragraph) == 1 and looks_like_heading(text):
                level = 3 if text.startswith("【") and text.endswith("】") else 2
                blocks.append(("heading", level, text))
            else:
                blocks.append(("p", text))
            paragraph = []

    def flush_quote():
        nonlocal quote
        if quote:
            blocks.append(("quote", " ".join(quote).strip()))
            quote = []

    def flush_list():
        nonlocal list_items, list_type
        if list_items:
            blocks.append((list_type, list_items))
            list_items = []
            list_type = None

    for raw_line in lines:
        stripped = raw_line.strip()

        if in_code:
            if CODE_FENCE_RE.match(stripped):
                blocks.append(("code", code_lang, "\n".join(code_lines)))
                in_code = False
                code_lang = ""
                code_lines = []
            else:
                code_lines.append(raw_line.rstrip("\n"))
            continue

        if not stripped:
            flush_paragraph()
            flush_quote()
            flush_list()
            continue

        fence = CODE_FENCE_RE.match(stripped)
        if fence:
            flush_paragraph()
            flush_quote()
            flush_list()
            in_code = True
            code_lang = fence.group(2).strip()
            code_lines = []
            continue

        match = HEADING_RE.match(stripped)
        if match:
            flush_paragraph()
            flush_quote()
            flush_list()
            level = min(len(match.group(1)) + 1, 6)
            blocks.append(("heading", level, match.group(2).strip()))
            continue

        if HR_RE.match(stripped):
            flush_paragraph()
            flush_quote()
            flush_list()
            blocks.append(("hr",))
            continue

        match = QUOTE_RE.match(stripped)
        if match:
            flush_paragraph()
            flush_list()
            quote.append(match.group(1).strip())
            continue

        match = UL_RE.match(stripped)
        if match:
            flush_paragraph()
            flush_quote()
            if list_type not in (None, "ul"):
                flush_list()
            list_type = "ul"
            list_items.append(match.group(1).strip())
            continue

        match = OL_RE.match(stripped)
        if match:
            flush_paragraph()
            flush_quote()
            if list_type not in (None, "ol"):
                flush_list()
            list_type = "ol"
            list_items.append(match.group(1).strip())
            continue

        flush_quote()
        if list_type and (raw_line.startswith(" ") or raw_line.startswith("\t")):
            list_items[-1] += " " + stripped
            continue
        if list_type:
            flush_list()
        paragraph.append(stripped)

    flush_paragraph()
    flush_quote()
    flush_list()

    rendered = []
    headings = []
    used_ids = set()

    for block in blocks:
        kind = block[0]
        if kind == "heading":
            _, level, text = block
            heading_id = slugify_heading(text, used_ids, len(headings) + 1)
            headings.append({"level": level, "text": text, "id": heading_id})
            rendered.append(
                "<h{level} id=\"{id}\">{text}</h{level}>".format(
                    level=level,
                    id=heading_id,
                    text=render_inline(text),
                )
            )
        elif kind == "p":
            rendered.append("<p>{}</p>".format(render_inline(block[1])))
        elif kind == "quote":
            rendered.append("<blockquote><p>{}</p></blockquote>".format(render_inline(block[1])))
        elif kind == "ul":
            rendered.append("<ul>{}</ul>".format("".join("<li>{}</li>".format(render_inline(item)) for item in block[1])))
        elif kind == "ol":
            rendered.append("<ol>{}</ol>".format("".join("<li>{}</li>".format(render_inline(item)) for item in block[1])))
        elif kind == "code":
            _, lang, code_text = block
            lang_class = ' class="language-{}"'.format(html.escape(lang, quote=True)) if lang else ""
            rendered.append(
                "<pre><code{lang}>{code}</code></pre>".format(
                    lang=lang_class,
                    code=html.escape(code_text, quote=False),
                )
            )
        elif kind == "hr":
            rendered.append("<hr>")

    return "\n".join(rendered), headings


def build():
    source_dir = pick_source_dir()
    records = []

    for path in sorted(source_dir.glob("*.md")):
        raw_text = path.read_text(encoding="utf-8-sig").strip()
        if not raw_text:
            continue

        meta, body = split_front_matter(raw_text)
        title = extract_title(body, meta, path.stem)
        body = remove_leading_title_block(body, title, path.stem)

        date_value = parse_date(meta.get("date")) or date_from_stem(path.stem)
        summary = meta.get("summary") or extract_summary(body, title, path.stem)
        content_html, headings = markdown_to_html(body)

        record = {
            "slug": path.stem,
            "title": title,
            "date": date_to_string(date_value),
            "summary": summary,
            "source": str(path.as_posix()),
            "content": body,
            "content_html": content_html,
            "headings": headings,
        }
        records.append((date_value or datetime.min, title, record))

    records.sort(key=lambda item: (item[0], item[1]), reverse=True)
    articles = [item[2] for item in records]

    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(exist_ok=True)

    with OUTPUT_LIST.open("w", encoding="utf-8") as handle:
        json.dump(
            [
                {
                    "slug": article["slug"],
                    "title": article["title"],
                    "date": article["date"],
                    "summary": article["summary"],
                    "source": article["source"],
                }
                for article in articles
            ],
            handle,
            ensure_ascii=False,
            indent=2,
        )

    for article in articles:
        target = OUTPUT_DIR / f"{article['slug']}.json"
        with target.open("w", encoding="utf-8") as handle:
            json.dump(article, handle, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    build()
