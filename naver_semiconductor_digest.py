#!/usr/bin/env python3
"""네이버 투자 블로그 반도체 글 수집/분석 데일리 리포트 생성기."""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import pathlib
import re
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Iterable

DEFAULT_KEYWORDS = [
    "반도체",
    "메모리",
    "HBM",
    "DRAM",
    "NAND",
    "파운드리",
    "TSMC",
    "삼성전자",
    "SK하이닉스",
    "AI",
    "CAPEX",
    "수요",
    "재고",
]


@dataclass
class Post:
    blog_id: str
    title: str
    link: str
    published: dt.datetime | None
    summary: str


@dataclass
class ScoredPost:
    post: Post
    matched_keywords: list[str]
    score: int


def load_config(config_path: pathlib.Path) -> dict:
    data = json.loads(config_path.read_text(encoding="utf-8"))
    if "blogs" not in data or not isinstance(data["blogs"], list):
        raise ValueError("config.json에 blogs 배열이 필요합니다.")

    data.setdefault("keywords", DEFAULT_KEYWORDS)
    data.setdefault("lookback_days", 1)
    return data


def fetch_rss(blog_id: str, timeout: int = 10) -> str:
    url = f"https://rss.blog.naver.com/{blog_id}.xml"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as res:
        return res.read().decode("utf-8", errors="replace")


def parse_rss(blog_id: str, rss_xml: str) -> list[Post]:
    root = ET.fromstring(rss_xml)
    items = root.findall("./channel/item")
    posts: list[Post] = []

    for item in items:
        title = text_or_empty(item.findtext("title"))
        link = text_or_empty(item.findtext("link"))
        description = html_to_text(text_or_empty(item.findtext("description")))
        pub_date_raw = text_or_empty(item.findtext("pubDate"))
        published = parse_pub_date(pub_date_raw)
        posts.append(
            Post(
                blog_id=blog_id,
                title=title,
                link=link,
                published=published,
                summary=description,
            )
        )

    return posts


def text_or_empty(value: str | None) -> str:
    return value.strip() if value else ""


def parse_pub_date(raw: str) -> dt.datetime | None:
    if not raw:
        return None
    fmts = [
        "%a, %d %b %Y %H:%M:%S %z",
        "%Y-%m-%d %H:%M:%S",
    ]
    for fmt in fmts:
        try:
            parsed = dt.datetime.strptime(raw, fmt)
            if parsed.tzinfo:
                return parsed.astimezone(dt.timezone.utc).replace(tzinfo=None)
            return parsed
        except ValueError:
            pass
    return None


def html_to_text(src: str) -> str:
    clean = re.sub(r"<br\s*/?>", "\n", src, flags=re.I)
    clean = re.sub(r"<[^>]+>", " ", clean)
    clean = html.unescape(clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


def within_days(post: Post, days: int, now: dt.datetime) -> bool:
    if post.published is None:
        return True
    return post.published >= now - dt.timedelta(days=days)


def score_post(post: Post, keywords: Iterable[str]) -> ScoredPost | None:
    corpus = f"{post.title} {post.summary}".lower()
    matched = [kw for kw in keywords if kw.lower() in corpus]
    if not matched:
        return None

    base = len(matched) * 10
    hot_terms = ["실적", "가이던스", "증설", "감산", "수주", "점유율"]
    hot_bonus = sum(5 for term in hot_terms if term in corpus)
    score = base + hot_bonus

    return ScoredPost(post=post, matched_keywords=matched, score=score)


def summarize(post: Post, max_sentences: int = 2) -> str:
    text = html_to_text(post.summary)
    sentences = re.split(r"(?<=[.!?。])\s+", text)
    selected = [s.strip() for s in sentences if len(s.strip()) >= 20][:max_sentences]
    if not selected:
        return text[:140]
    return " ".join(selected)


def build_report(scored_posts: list[ScoredPost], generated_at: dt.datetime) -> str:
    header = [
        "# 반도체 투자 블로그 데일리 체크",
        f"- 생성 시각: {generated_at.strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 총 중요 글: {len(scored_posts)}건",
        "",
    ]

    body: list[str] = []
    for idx, item in enumerate(scored_posts, start=1):
        date_str = (
            item.post.published.strftime("%Y-%m-%d %H:%M") if item.post.published else "날짜 미상"
        )
        body.extend(
            [
                f"## {idx}. {item.post.title}",
                f"- 블로그: `{item.post.blog_id}`",
                f"- 게시일: {date_str}",
                f"- 중요도 점수: **{item.score}**",
                f"- 감지 키워드: {', '.join(item.matched_keywords)}",
                f"- 핵심 요약: {summarize(item.post)}",
                f"- 링크: {item.post.link}",
                "",
            ]
        )

    if not body:
        body = ["오늘은 설정한 키워드 조건을 만족하는 신규 글이 없습니다.", ""]

    return "\n".join(header + body)


def run(config_path: pathlib.Path, output_path: pathlib.Path, now: dt.datetime | None = None) -> None:
    config = load_config(config_path)
    now = now or dt.datetime.utcnow()

    posts: list[Post] = []
    for blog_id in config["blogs"]:
        try:
            xml = fetch_rss(blog_id)
            posts.extend(parse_rss(blog_id, xml))
        except (urllib.error.URLError, ET.ParseError) as exc:
            print(f"[WARN] {blog_id} RSS 처리 실패: {exc}")

    filtered = [p for p in posts if within_days(p, config["lookback_days"], now)]

    scored: list[ScoredPost] = []
    for post in filtered:
        scored_post = score_post(post, config["keywords"])
        if scored_post:
            scored.append(scored_post)

    scored.sort(
        key=lambda x: (
            x.score,
            x.post.published or dt.datetime.min,
        ),
        reverse=True,
    )

    report = build_report(scored, generated_at=now)
    output_path.write_text(report, encoding="utf-8")
    print(f"완료: {output_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="네이버 반도체 투자 블로그 데일리 리포트")
    parser.add_argument("--config", default="config.json", help="설정 파일 경로(JSON)")
    parser.add_argument("--output", default="reports/daily_report.md", help="리포트 출력 경로")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_path = pathlib.Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    run(pathlib.Path(args.config), output_path)


if __name__ == "__main__":
    main()
