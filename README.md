# godonepick-codex

국내 네이버 유명 투자 블로그에서 **반도체 관련 글**을 수집하고,
키워드 기반으로 중요도를 계산해 데일리 요약 리포트를 만드는 프로그램입니다.

## 구성 파일

- `naver_semiconductor_digest.py`: RSS 수집/필터링/요약/리포트 생성 스크립트
- `config.example.json`: 블로그 ID, 키워드, 조회 기간 예시 설정
- `tests/test_digest.py`: 핵심 로직 테스트

## 빠른 시작

1. 설정 파일 생성

```bash
cp config.example.json config.json
```

`config.json`의 `blogs`에 네이버 블로그 ID를 넣으세요.

2. 실행

```bash
python naver_semiconductor_digest.py --config config.json --output reports/daily_report.md
```

3. 결과 확인

- `reports/daily_report.md`에 중요 글 목록과 핵심 요약이 저장됩니다.

## 자동 실행 (매일 오전 8시 예시)

```bash
0 8 * * * cd /workspace/godonepick-codex && /usr/bin/python3 naver_semiconductor_digest.py --config config.json --output reports/daily_report.md
```

## 테스트

```bash
python -m pytest -q
```

## 동작 방식

1. `https://rss.blog.naver.com/{blog_id}.xml`에서 최신 글 수집
2. 최근 `lookback_days` 기간 글만 선별
3. 반도체 키워드 매칭 + 보너스 용어(실적/증설/점유율 등)로 점수화
4. 점수순으로 정렬해 Markdown 리포트 생성

## 참고

- 네이버 블로그 RSS 공개 여부에 따라 일부 블로그는 수집이 실패할 수 있습니다.
- 더 정교한 분석이 필요하면 요약/점수화 함수에 LLM API 또는 형태소 분석기를 추가해 확장 가능합니다.

## 메르 최신글 자동 요약 HTML (실행형)

요청하신 것처럼 메르(`ranto28`) 최신글을 자동으로 가져와 요약/분석해서 HTML로 출력할 수 있습니다.

### 1) 1회 생성

```bash
python mer_blog_html_digest.py --output reports/mer_latest_dashboard.html --refresh-seconds 600
```

생성된 파일을 브라우저로 열면 최신글 요약/체크포인트/최근글 목록을 볼 수 있습니다.

### 2) 자동 갱신(watch)

```bash
python mer_blog_html_digest.py --watch --interval 600 --output reports/mer_latest_dashboard.html
```

- `--interval`: RSS 재조회 주기(초)
- `--refresh-seconds`: HTML 자체 새로고침 간격(초)
- `--rss-file`: 네트워크 제한 환경에서 사용할 로컬 RSS(XML) 파일 경로

네트워크가 제한되어 RSS 접근이 막히면, 스크립트는 실패하지 않고 오류 안내가 포함된 HTML을 생성합니다.
