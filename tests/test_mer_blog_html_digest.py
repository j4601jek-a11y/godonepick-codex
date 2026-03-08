import datetime as dt

from mer_blog_html_digest import Post, detect_topics, parse_posts, render_html, summarize_text

SAMPLE_RSS = """<?xml version='1.0' encoding='UTF-8'?>
<rss>
  <channel>
    <item>
      <title>호르무즈 해협과 유가 급등 이슈</title>
      <link>https://blog.naver.com/ranto28/1</link>
      <description><![CDATA[<p>이란 관련 긴장으로 원유, LNG 가격 변동성이 커졌다. 시장은 환율과 물가를 동시에 본다.</p>]]></description>
      <pubDate>Tue, 11 Feb 2025 09:00:00 +0900</pubDate>
    </item>
  </channel>
</rss>
"""


def test_parse_posts_and_topics():
    posts = parse_posts(SAMPLE_RSS)
    assert len(posts) == 1
    tags = detect_topics(posts[0])
    assert "지정학" in tags
    assert "에너지" in tags


def test_render_html_contains_latest_title():
    post = Post(
        title="테스트 글",
        link="https://blog.naver.com/ranto28/2",
        published=dt.datetime(2025, 2, 11, 0, 0, 0),
        summary="주식 시장과 금리, 환율 이슈를 요약합니다.",
    )
    html_doc = render_html([post], generated_at=dt.datetime(2025, 2, 11, 1, 0, 0), refresh_seconds=300)
    assert "메르 블로그 자동 요약 대시보드" in html_doc
    assert "테스트 글" in html_doc
    assert "300초" in html_doc


def test_summarize_text_fallback():
    short = summarize_text("짧은 문장")
    assert short
