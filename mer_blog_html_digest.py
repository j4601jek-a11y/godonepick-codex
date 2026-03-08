#!/usr/bin/env python3
"""메르 네이버 블로그 최신글 자동 요약/분석 HTML 생성기."""

from __future__ import annotations

import argparse
import datetime as dt
import html
import pathlib
import re
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass

RSS_URL = "https://rss.blog.naver.com/ranto28.xml"

TOPIC_KEYWORDS = {
    "지정학": ["이란", "이스라엘", "중동", "전쟁", "호르무즈", "제재", "분쟁"],
    "에너지": ["원유", "유가", "천연가스", "LNG", "정유", "경유", "휘발유"],
    "물류/해운": ["해협", "운임", "물류", "선박", "항로", "보험료"],
    "거시경제": ["금리", "환율", "인플레", "물가", "성장", "침체"],
    "주식시장": ["주식", "밸류", "실적", "EPS", "PER", "리스크", "매수", "매도"],
}


@dataclass
class Post:
    title: str
    link: str
    published: dt.datetime | None
    summary: str


def fetch_rss(url: str = RSS_URL, timeout: int = 15) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as res:
        return res.read().decode("utf-8", errors="replace")


def strip_html(src: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n", src, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def parse_pub_date(value: str) -> dt.datetime | None:
    if not value:
        return None
    fmts = ["%a, %d %b %Y %H:%M:%S %z", "%Y-%m-%d %H:%M:%S"]
    for fmt in fmts:
        try:
            parsed = dt.datetime.strptime(value.strip(), fmt)
            if parsed.tzinfo:
                return parsed.astimezone(dt.timezone.utc).replace(tzinfo=None)
            return parsed
        except ValueError:
            continue
    return None


def parse_posts(rss_xml: str) -> list[Post]:
    root = ET.fromstring(rss_xml)
    items = root.findall("./channel/item")
    posts: list[Post] = []
    for item in items:
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        raw_desc = (item.findtext("description") or "").strip()
        pub_date = parse_pub_date(item.findtext("pubDate") or "")
        posts.append(Post(title=title, link=link, published=pub_date, summary=strip_html(raw_desc)))
    posts.sort(key=lambda p: p.published or dt.datetime.min, reverse=True)
    return posts


def summarize_text(text: str, max_sentences: int = 3) -> str:
    if not text:
        return "요약할 본문 정보가 부족합니다."
    sentences = re.split(r"(?<=[.!?。])\s+", text)
    selected = [s.strip() for s in sentences if len(s.strip()) >= 18][:max_sentences]
    if selected:
        return " ".join(selected)
    return text[:220]


def detect_topics(post: Post) -> list[str]:
    corpus = f"{post.title} {post.summary}"
    tags: list[str] = []
    for topic, keywords in TOPIC_KEYWORDS.items():
        if any(kw in corpus for kw in keywords):
            tags.append(topic)
    return tags or ["기타"]


def analysis_points(post: Post) -> list[str]:
    tags = detect_topics(post)
    points: list[str] = []

    if "지정학" in tags:
        points.append("지정학 이슈가 시장 변동성(유가·환율·리스크 프리미엄)을 확대시킬 가능성이 있습니다.")
    if "에너지" in tags:
        points.append("에너지 가격 변화는 한국 증시에서 정유/화학/운송 업종의 상대 강약에 영향을 줄 수 있습니다.")
    if "물류/해운" in tags:
        points.append("해운/물류 차질 신호는 운임과 공급망 비용 상승 가능성을 점검할 필요가 있습니다.")
    if "거시경제" in tags:
        points.append("거시 변수(금리·환율·물가)와 동시 확인해야 해석 오류를 줄일 수 있습니다.")
    if "주식시장" in tags:
        points.append("단기 뉴스 추격보다 실적/밸류에이션/수급 데이터로 교차검증하는 접근이 유효합니다.")

    if not points:
        points.append("핵심 수치(가격·실적·정책 발표)와 함께 원문을 재확인하는 것이 안전합니다.")

    return points[:4]


def fmt_date(value: dt.datetime | None) -> str:
    if not value:
        return "날짜 미상"
    return value.strftime("%Y-%m-%d %H:%M UTC")


def render_html(posts: list[Post], generated_at: dt.datetime, refresh_seconds: int) -> str:
    latest = posts[0] if posts else None

    latest_html = ""
    if latest:
        latest_summary = summarize_text(latest.summary)
        latest_tags = ", ".join(detect_topics(latest))
        latest_points = "".join(f"<li>{html.escape(p)}</li>" for p in analysis_points(latest))
        latest_html = f"""
        <section class=\"card\">
          <h2>최신글</h2>
          <h3>{html.escape(latest.title)}</h3>
          <p><strong>게시일:</strong> {fmt_date(latest.published)}</p>
          <p><strong>분류 태그:</strong> {html.escape(latest_tags)}</p>
          <p><strong>요약:</strong> {html.escape(latest_summary)}</p>
          <p><a href=\"{html.escape(latest.link)}\" target=\"_blank\">원문 보기</a></p>
          <h4>투자 관점 체크포인트</h4>
          <ul>{latest_points}</ul>
        </section>
        """
    else:
        latest_html = "<section class=\"card\"><h2>최신글</h2><p>가져온 글이 없습니다.</p></section>"

    recent_cards = []
    for post in posts[:8]:
        recent_cards.append(
            f"""
            <li>
              <a href=\"{html.escape(post.link)}\" target=\"_blank\">{html.escape(post.title)}</a>
              <span>{fmt_date(post.published)}</span>
            </li>
            """
        )

    recent_html = "\n".join(recent_cards) if recent_cards else "<li>표시할 글 없음</li>"

    return f"""<!doctype html>
<html lang=\"ko\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <meta http-equiv=\"refresh\" content=\"{refresh_seconds}\" />
  <title>메르 블로그 자동 요약 대시보드</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 0; background: #f4f6f8; color: #1f2937; }}
    .wrap {{ max-width: 920px; margin: 24px auto; padding: 0 16px; }}
    .card {{ background: #fff; border-radius: 12px; padding: 18px; margin-bottom: 16px; box-shadow: 0 2px 10px rgba(0,0,0,0.06); }}
    h1 {{ margin-bottom: 8px; }}
    h2 {{ margin-top: 0; }}
    h3 {{ margin-top: 10px; margin-bottom: 8px; }}
    ul {{ padding-left: 20px; }}
    li {{ margin-bottom: 8px; }}
    .muted {{ color: #6b7280; font-size: 14px; }}
    .recent li span {{ display: inline-block; margin-left: 8px; color: #6b7280; font-size: 13px; }}
    a {{ color: #2563eb; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
  </style>
</head>
<body>
  <div class=\"wrap\">
    <section class=\"card\">
      <h1>메르 블로그 자동 요약 대시보드</h1>
      <p class=\"muted\">생성 시각: {generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')} / 자동 새로고침: {refresh_seconds}초</p>
      <p class=\"muted\">데이터 소스: {RSS_URL}</p>
    </section>
    {latest_html}
    <section class=\"card recent\">
      <h2>최근 글 목록</h2>
      <ul>
        {recent_html}
      </ul>
    </section>
  </div>
</body>
</html>
"""


def render_error_html(message: str, generated_at: dt.datetime) -> str:
    return f"""<!doctype html>
<html lang=\"ko\">
<head><meta charset=\"utf-8\"><title>메르 블로그 자동 요약 대시보드</title></head>
<body style=\"font-family:sans-serif;padding:20px;\">
  <h1>메르 블로그 자동 요약 대시보드</h1>
  <p>생성 시각: {generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
  <p style=\"color:#b91c1c;\">RSS 조회 실패: {html.escape(message)}</p>
  <p>네트워크가 제한된 환경일 수 있습니다. 잠시 후 다시 실행하거나, --rss-file 옵션으로 로컬 XML을 지정하세요.</p>
</body></html>
"""


def generate_once(output_path: pathlib.Path, refresh_seconds: int, rss_file: pathlib.Path | None = None) -> None:
    generated_at = dt.datetime.utcnow()
    try:
        if rss_file:
            rss_xml = rss_file.read_text(encoding="utf-8")
        else:
            rss_xml = fetch_rss()
        posts = parse_posts(rss_xml)
        html_doc = render_html(posts, generated_at=generated_at, refresh_seconds=refresh_seconds)
    except (urllib.error.URLError, OSError, ET.ParseError, FileNotFoundError) as exc:
        html_doc = render_error_html(str(exc), generated_at=generated_at)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html_doc, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="메르 블로그 최신글 자동 HTML 요약")
    parser.add_argument("--output", default="reports/mer_latest_dashboard.html", help="HTML 출력 파일")
    parser.add_argument("--refresh-seconds", type=int, default=600, help="HTML 자동 새로고침 간격(초)")
    parser.add_argument("--watch", action="store_true", help="주기적으로 RSS를 재조회하여 파일 갱신")
    parser.add_argument("--interval", type=int, default=600, help="watch 모드 재조회 주기(초)")
    parser.add_argument("--rss-file", default="", help="네트워크 제한 시 사용할 로컬 RSS XML 파일")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out = pathlib.Path(args.output)

    rss_file = pathlib.Path(args.rss_file) if args.rss_file else None

    if args.watch:
        print(f"[INFO] watch 모드 시작: interval={args.interval}s, output={out}")
        while True:
            try:
                generate_once(out, refresh_seconds=args.refresh_seconds, rss_file=rss_file)
                print(f"[OK] {dt.datetime.now().strftime('%H:%M:%S')} 업데이트 완료")
            except Exception as exc:  # noqa: BLE001
                print(f"[WARN] 갱신 실패: {exc}")
            time.sleep(max(args.interval, 30))
    else:
        generate_once(out, refresh_seconds=args.refresh_seconds, rss_file=rss_file)
        print(f"[OK] 생성 완료: {out}")


if __name__ == "__main__":
    main()
