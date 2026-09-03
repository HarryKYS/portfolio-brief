"""국면 판단 — 규칙 기반. LLM도 유료 API도 쓰지 않는다.

각 신호는 -1(위험) / 0(중립) / +1(우호) 중 하나를 내고, 합으로 등급을 매긴다.
신호를 '왜' 그렇게 읽었는지를 문자열로 같이 반환한다 — 근거 없는 등급은 쓸모가 없다.
"""
from __future__ import annotations

from dataclasses import dataclass

from collect import Market

# 임계값. 매직넘버를 코드에 흩뿌리지 않는다.
VIX_CALM, VIX_STRESS = 20.0, 30.0
USDKRW_HIGH = 1_400.0
US10Y_HIGH = 4.5
GOLD_DIP = -10.0          # 고점 대비 이만큼 빠지면 분할 진입 조건 충족
DEEP_DRAWDOWN = -20.0     # 고점 대비 -20%는 통상 약세장 정의


@dataclass(frozen=True)
class Signal:
    key: str
    label: str
    score: int          # -1 / 0 / +1
    detail: str


@dataclass(frozen=True)
class Regime:
    grade: str          # 공격 / 중립 / 방어
    score: int
    signals: list[Signal]

    @property
    def risk_count(self) -> int:
        return sum(1 for s in self.signals if s.score < 0)


def _trend(mkt: Market, name: str, key: str, label: str) -> Signal | None:
    """200일선 대비 위치 = 추세. 절대모멘텀의 가장 단순한 형태."""
    q = mkt.get(name)
    if q is None:
        return None
    if q.above_ma200:
        score, verdict = 1, "상승 추세"
    else:
        score, verdict = -1, "하락 추세"
    return Signal(key, label, score,
                  f"{q.name} {q.last:,.0f} · 200일선 {q.vs_ma200:+.1f}% ({verdict}) · 고점대비 {q.from_high:+.1f}%")


def evaluate(mkt: Market) -> Regime:
    sigs: list[Signal] = []

    for name, key, label in (("코스피", "kr_trend", "한국 대형주 추세"),
                             ("코스닥", "kq_trend", "한국 중소형 추세"),
                             ("S&P500", "us_trend", "미국 추세")):
        s = _trend(mkt, name, key, label)
        if s:
            sigs.append(s)

    # 변동성 — 낮다고 무조건 좋은 건 아니지만, 높으면 확실히 위험하다.
    vix = mkt.get("VIX")
    if vix:
        if vix.last >= VIX_STRESS:
            sigs.append(Signal("vix", "변동성", -1, f"VIX {vix.last:.1f} — 공포 구간(≥{VIX_STRESS:.0f})"))
        elif vix.last >= VIX_CALM:
            sigs.append(Signal("vix", "변동성", 0, f"VIX {vix.last:.1f} — 경계(≥{VIX_CALM:.0f})"))
        else:
            sigs.append(Signal("vix", "변동성", 1, f"VIX {vix.last:.1f} — 안정"))

    # 금리 — 이 국면의 진짜 압력점. 장기금리가 높으면 주식·채권이 같이 눌린다.
    tnx = mkt.get("미국채10년")
    if tnx:
        at_high = tnx.from_high > -1.0
        if tnx.last >= US10Y_HIGH and at_high:
            sigs.append(Signal("rate", "장기금리", -1,
                               f"미 10년 {tnx.last:.2f}% — 1년 최고권. 장기채 금지, 주식 밸류에이션 압박"))
        elif tnx.last >= US10Y_HIGH:
            sigs.append(Signal("rate", "장기금리", 0, f"미 10년 {tnx.last:.2f}% — 높지만 고점은 지남"))
        else:
            sigs.append(Signal("rate", "장기금리", 1, f"미 10년 {tnx.last:.2f}% — 부담 완화"))

    # 환율 — 해외자산 환전 조건. 높으면 사기 나쁘고, 낮으면 유리하다.
    fx = mkt.get("원/달러")
    if fx:
        if fx.last >= USDKRW_HIGH:
            sigs.append(Signal("fx", "환율", -1,
                               f"원/달러 {fx.last:,.0f} — 고환율. 해외자산 신규 환전 불리, 분할 필수"))
        else:
            sigs.append(Signal("fx", "환율", 1,
                               f"원/달러 {fx.last:,.0f} (고점대비 {fx.from_high:+.1f}%) — 환전 조건 양호"))

    # 반도체 — 한국 지수의 절반이 여기 걸려 있다. 별도 신호로 뽑는다.
    sox = mkt.get("필라델피아반도체")
    if sox:
        if sox.from_high <= DEEP_DRAWDOWN:
            sigs.append(Signal("semi", "반도체 사이클", -1,
                               f"필라델피아반도체 고점대비 {sox.from_high:+.1f}% — 사이클 둔화. "
                               f"코스피 시총 절반이 메모리 2종목이라 국내 지수에 직결"))
        else:
            sigs.append(Signal("semi", "반도체 사이클", 1,
                               f"필라델피아반도체 고점대비 {sox.from_high:+.1f}% — 사이클 유지"))

    score = sum(s.score for s in sigs)
    n = len(sigs) or 1
    ratio = score / n
    if ratio >= 0.4:
        grade = "공격"
    elif ratio >= -0.1:
        grade = "중립"
    else:
        grade = "방어"
    return Regime(grade=grade, score=score, signals=sigs)


def tactical_notes(mkt: Market) -> list[str]:
    """등급과 별개로, 오늘 눈에 띄는 것만 짧게. 없으면 빈 리스트."""
    out: list[str] = []
    gold = mkt.get("금")
    if gold and gold.from_high <= GOLD_DIP:
        out.append(f"금 고점대비 {gold.from_high:+.1f}% — 목표 10% 분할 진입 조건 충족")
    kq, ks = mkt.get("코스닥"), mkt.get("코스피")
    if kq and ks and not kq.above_ma200 and ks.above_ma200:
        out.append("코스닥만 200일선 아래 — 국내는 대형주로만, 중소형 분산 보류")
    tnx = mkt.get("미국채10년")
    if tnx and tnx.last >= US10Y_HIGH:
        out.append(f"미 10년 {tnx.last:.2f}% — 장기채(TLT류) 매수 금지, 채권은 단기·중기로만")
    return out


if __name__ == "__main__":
    import collect
    r = evaluate(collect.fetch())
    print(f"국면: {r.grade} (score {r.score:+d}, 위험신호 {r.risk_count}개)")
    for s in r.signals:
        mark = {1: "🟢", 0: "🟡", -1: "🔴"}[s.score]
        print(f"  {mark} {s.label}: {s.detail}")
