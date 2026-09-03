#!/usr/bin/env python3
"""공개 페이지 생성 — 시장 데이터와 국면만 담는다.

개인 수치(보유액·이탈도·주거 D-day·세액공제 잔여)는 **절대 여기 넣지 않는다.**
GitHub Pages는 무료 플랜에서 공개 저장소만 지원하므로, 이 페이지는 열린 웹에 노출된다.
개인 숫자는 텔레그램 브리핑에만 있다.
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import collect
import regime

ROOT = Path(__file__).resolve().parent
KST = timezone(timedelta(hours=9))

# 표에 넣을 순서. collect.TICKERS 의 표시명과 일치해야 한다.
TABLE_ROWS = ("코스피", "코스닥", "삼성전자", "SK하이닉스", "필라델피아반도체",
              "S&P500", "나스닥", "미국채10년", "VIX", "원/달러", "금", "비트코인")
HIGHLIGHT = {"코스피", "코스닥", "미국채10년"}
# 한국 증시 관례: 상승=빨강(up), 하락=파랑(dn)
MARK_CLASS = {1: "sig-ok", 0: "sig-mid", -1: "sig-bad"}
MARK_LABEL = {1: "양호", 0: "주의", -1: "위험"}


def esc(text: str) -> str:
    return (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def pct(value: float) -> str:
    """부호에 따라 한국 관례 색을 입힌다."""
    cls = "up" if value > 0 else ("dn" if value < 0 else "")
    return f'<td class="num {cls}">{value:+.1f}%</td>'


def price(q: collect.Quote) -> str:
    if q.name == "미국채10년":
        return f"{q.last:.2f}%"
    if q.name in ("금", "비트코인"):
        return f"${q.last:,.0f}"
    if q.name == "VIX":
        return f"{q.last:.1f}"
    if q.last >= 10_000:
        return f"{q.last:,.0f}"
    return f"{q.last:,.1f}"


def market_section(mkt: collect.Market) -> str:
    rows = []
    for name in TABLE_ROWS:
        q = mkt.get(name)
        if q is None:
            continue
        cls = ' class="hl"' if name in HIGHLIGHT else ""
        rows.append(
            f"<tr{cls}><td>{esc(q.name)}</td>"
            f'<td class="num">{price(q)}</td>'
            f"{pct(q.from_high)}{pct(q.vs_ma200)}{pct(q.ytd)}</tr>"
        )
    if not rows:
        return ('<section><div class="sec-head"><span class="sec-n">01</span>'
                "<h2>오늘의 시장</h2></div><p>시장 데이터를 받지 못했다.</p></section>")
    err = ""
    if mkt.errors:
        err = ('<p style="color:var(--warn);font-size:.85rem">⚠️ 일부 수집 실패: '
               + esc(", ".join(mkt.errors)) + "</p>")
    return f"""<section>
  <div class="sec-head"><span class="sec-n">01</span><h2>오늘의 시장</h2></div>
  <p>한국 증시 관례대로 <span class="up">상승은 빨강</span>,
     <span class="dn">하락은 파랑</span>으로 표시했다. 매일 자동 갱신된다.</p>
  {err}
  <div class="tw">
  <table>
    <caption>200일선 대비는 추세, 고점 대비는 1년 최고가에서의 조정 폭을 뜻한다.</caption>
    <thead><tr><th>자산</th><th>현재가</th><th>1년 고점 대비</th><th>200일선 대비</th><th>연초 대비</th></tr></thead>
    <tbody>{"".join(rows)}</tbody>
  </table>
  </div>
</section>"""


def live_section(reg: regime.Regime, mkt: collect.Market) -> str:
    sigs = "".join(
        f'<li class="{MARK_CLASS[s.score]}"><span class="sig-tag">{MARK_LABEL[s.score]}</span>'
        f"<span>{esc(s.detail)}</span></li>"
        for s in reg.signals
    )
    notes = regime.tactical_notes(mkt)
    note_html = ""
    if notes:
        note_html = ('<div class="notes"><b>오늘 눈에 띄는 것</b><ul>'
                     + "".join(f"<li>{esc(n)}</li>" for n in notes) + "</ul></div>")
    grade_cls = {"공격": "sig-ok", "중립": "sig-mid", "방어": "sig-bad"}[reg.grade]
    return f"""<div class="live">
  <div class="live-head">
    <span class="tag">라이브 · 매일 자동 갱신</span>
    <div class="grade {grade_cls}"><b>{reg.grade}</b>
      <span>신호 {len(reg.signals)}개 중 위험 {reg.risk_count}개</span></div>
  </div>
  <ul class="sigs">{sigs}</ul>
  {note_html}
</div>"""


LIVE_CSS = """
<style>
.live{background:var(--surface);border:1px solid var(--hair);border-top:3px solid var(--accent);
  padding:1.4rem 1.6rem;margin-bottom:2.5rem}
.live-head{display:flex;flex-wrap:wrap;gap:.9rem 1.5rem;align-items:center;justify-content:space-between;
  border-bottom:1px solid var(--hair);padding-bottom:.9rem;margin-bottom:1rem}
.live .tag{font-family:var(--mono);font-size:.7rem;letter-spacing:.14em;text-transform:uppercase;
  color:var(--accent);font-weight:600}
.grade{display:flex;align-items:baseline;gap:.6rem}
.grade b{font-family:var(--serif);font-size:1.6rem;line-height:1}
.grade span{font-family:var(--mono);font-size:.74rem;color:var(--muted)}
.grade.sig-ok b{color:var(--accent)} .grade.sig-mid b{color:var(--warn)} .grade.sig-bad b{color:var(--up)}
.sigs{list-style:none;margin:0;padding:0;display:grid;gap:.55rem}
.sigs li{display:grid;grid-template-columns:3.2rem 1fr;gap:.85rem;align-items:start;font-size:.88rem;
  color:var(--ink-2);line-height:1.6}
.sig-tag{font-family:var(--mono);font-size:.68rem;letter-spacing:.06em;text-align:center;
  padding:.16rem 0;border:1px solid currentColor;white-space:nowrap;margin-top:.15rem}
.sigs li.sig-ok .sig-tag{color:var(--accent)}
.sigs li.sig-mid .sig-tag{color:var(--warn)}
.sigs li.sig-bad .sig-tag{color:var(--up)}
.notes{margin-top:1.1rem;padding-top:.95rem;border-top:1px solid var(--hair)}
.notes b{font-family:var(--mono);font-size:.7rem;letter-spacing:.12em;text-transform:uppercase;
  color:var(--muted);font-weight:600}
.notes ul{margin:.55rem 0 0;padding-left:1.1rem;font-size:.88rem;color:var(--ink-2);line-height:1.65}
.notes li{margin-bottom:.3rem}
@media(max-width:520px){.sigs li{grid-template-columns:1fr;gap:.25rem}
  .sig-tag{justify-self:start;padding:.16rem .5rem}}
</style>
"""


def main() -> int:
    mkt = collect.fetch()
    if not mkt.quotes:
        print("시장 데이터를 하나도 받지 못했다. 기존 index.html을 유지한다.", file=sys.stderr)
        for e in mkt.errors:
            print(" ", e, file=sys.stderr)
        return 1                      # 조용히 빈 페이지를 덮어쓰지 않는다
    reg = regime.evaluate(mkt)
    now = datetime.now(KST)
    html = (ROOT / "template.html").read_text()
    html = (html
            .replace("{{UPDATED}}", now.strftime("%Y-%m-%d %H:%M KST"))
            .replace("{{LIVE}}", live_section(reg, mkt))
            .replace("{{MARKET}}", market_section(mkt)))
    # 라이브 블록 전용 CSS를 </style> 뒤가 아니라 첫 <style> 블록 다음에 붙인다.
    html = html.replace("</style>", "</style>" + LIVE_CSS, 1)
    (ROOT / "index.html").write_text(html)
    print(f"index.html 생성 · 국면 {reg.grade} · 지표 {len(mkt.quotes)}개 · {now:%Y-%m-%d %H:%M}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
