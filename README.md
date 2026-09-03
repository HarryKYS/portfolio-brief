# 투자 포트폴리오 설계서 (공개 페이지)

https://harrykys.github.io/portfolio-brief/

자산배분 설계 프레임워크와 **매일 자동 갱신되는 시장·국면 판단**.

## 이 저장소에 없는 것

개인 보유액, 포트폴리오 이탈도, 주거자금 D-day, 세액공제 잔여 한도 등
**사적인 수치는 여기 들어오지 않는다.** GitHub Pages는 무료 플랜에서 공개 저장소만
지원하므로 이 페이지는 열린 웹에 노출된다. 개인 숫자는 텔레그램 브리핑에만 있다.

원본 프로젝트(비공개): `~/Desktop/Harry Projects/투자-포트폴리오/`

## 구성

| 파일 | 역할 |
|---|---|
| `template.html` | 설계 본문 (정적) + `{{UPDATED}}` `{{LIVE}}` `{{MARKET}}` 플레이스홀더 |
| `collect.py` | yfinance 시장 데이터 수집 |
| `regime.py` | 규칙 기반 국면 판단 (LLM·유료 API 없음) |
| `build.py` | 템플릿 + 라이브 데이터 → `index.html` |
| `.github/workflows/daily.yml` | KST 07:40 / 18:40 자동 갱신 |

## 로컬 실행

```bash
pip install -r requirements.txt
python build.py        # index.html 재생성
```

시장 데이터를 하나도 받지 못하면 exit 1로 끝나고 **기존 index.html을 덮어쓰지 않는다.**
빈 페이지가 배포되는 것보다 어제 데이터가 남는 편이 낫다.
