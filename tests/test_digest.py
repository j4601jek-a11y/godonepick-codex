import datetime as dt

from naver_semiconductor_digest import parse_rss, score_post, within_days

SAMPLE_RSS = """<?xml version='1.0' encoding='UTF-8'?>
<rss>
  <channel>
    <item>
      <title>HBM 공급 확대와 삼성전자 수요 전망</title>
      <link>https://blog.naver.com/sample/1</link>
      <description><![CDATA[<p>반도체 업황 회복과 함께 HBM 수요가 증가.</p>]]></description>
      <pubDate>Tue, 11 Feb 2025 09:00:00 +0900</pubDate>
    </item>
  </channel>
</rss>
"""


def test_parse_and_score():
    posts = parse_rss("sample", SAMPLE_RSS)
    assert len(posts) == 1
    scored = score_post(posts[0], ["반도체", "HBM", "파운드리"])
    assert scored is not None
    assert scored.score >= 20
    assert "HBM" in scored.matched_keywords


def test_within_days():
    post = parse_rss("sample", SAMPLE_RSS)[0]
    now = dt.datetime(2025, 2, 11, 10, 0, 0)
    assert within_days(post, 2, now)
    assert not within_days(post, 0, now)
