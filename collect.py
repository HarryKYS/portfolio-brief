"""시장 데이터 수집 — 전부 무료 소스(yfinance)만 쓴다.

유료 API를 쓰지 않는 게 이 프로젝트의 고정 제약이다.
실패한 티커는 조용히 버리지 않고 errors에 남긴다 — 조용한 실패가 가장 위험하다.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field

import yfinance as yf

# 티커 → (표시명, 그룹). 그룹은 브리핑 정렬용.
TICKERS: dict[str, tuple[str, str]] = {
    "^KS11":   ("코스피", "kr"),
    "^KQ11":   ("코스닥", "kr"),
    "005930.KS": ("삼성전자", "kr"),
    "000660.KS": ("SK하이닉스", "kr"),
    "^GSPC":   ("S&P500", "us"),
    "^IXIC":   ("나스닥", "us"),
    "^SOX":    ("필라델피아반도체", "us"),
    "^VIX":    ("VIX", "risk"),
    "^TNX":    ("미국채10년", "rate"),
    "KRW=X":   ("원/달러", "fx"),
    "GC=F":    ("금", "real"),
    "BTC-USD": ("비트코인", "real"),
}

MA_WINDOW = 200


@dataclass
class Quote:
    ticker: str
    name: str
    group: str
    last: float
    prev: float
    ma200: float
    high_1y: float
    high_date: str
    ytd_start: float

    @property
    def chg_pct(self) -> float:
        return (self.last / self.prev - 1) * 100 if self.prev else 0.0

    @property
    def vs_ma200(self) -> float:
        return (self.last / self.ma200 - 1) * 100 if self.ma200 else 0.0

    @property
    def from_high(self) -> float:
        return (self.last / self.high_1y - 1) * 100 if self.high_1y else 0.0

    @property
    def ytd(self) -> float:
        return (self.last / self.ytd_start - 1) * 100 if self.ytd_start else 0.0

    @property
    def above_ma200(self) -> bool:
        return self.last > self.ma200 > 0


@dataclass
class Market:
    quotes: dict[str, Quote] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    def get(self, name: str) -> Quote | None:
        return self.quotes.get(name)


def fetch(tickers: dict[str, tuple[str, str]] | None = None) -> Market:
    tickers = tickers or TICKERS
    mkt = Market()
    for tk, (name, group) in tickers.items():
        try:
            hist = yf.Ticker(tk).history(period="1y")["Close"].dropna()
        except Exception as exc:                      # noqa: BLE001 — 소스 장애 종류를 가리지 않는다
            mkt.errors.append(f"{name}({tk}) 수집 실패: {type(exc).__name__}")
            continue
        if len(hist) < 2:
            mkt.errors.append(f"{name}({tk}) 데이터 부족(rows={len(hist)})")
            continue
        year = hist.index[-1].year
        ytd_slice = hist[hist.index >= f"{year}-01-01"]
        mkt.quotes[name] = Quote(
            ticker=tk,
            name=name,
            group=group,
            last=float(hist.iloc[-1]),
            prev=float(hist.iloc[-2]),
            ma200=float(hist.tail(MA_WINDOW).mean()),
            high_1y=float(hist.max()),
            high_date=str(hist.idxmax().date()),
            ytd_start=float(ytd_slice.iloc[0]) if len(ytd_slice) else float(hist.iloc[0]),
        )
    return mkt


if __name__ == "__main__":
    m = fetch()
    for q in m.quotes.values():
        print(f"{q.name:16s} {q.last:12,.2f} {q.chg_pct:+6.2f}% "
              f"MA200{q.vs_ma200:+7.1f}% 고점대비{q.from_high:+7.1f}% YTD{q.ytd:+7.1f}%")
    for e in m.errors:
        print("ERR", e, file=sys.stderr)
