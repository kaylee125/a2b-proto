"""하락장 검증: 서울 25구 단지를 과거 여러 기준일로 엔진에 돌려 상태 분포를 보고, 같은 시점의 '다른 방법' 두 가지와 비교한다.
  (1) 단순 기준: 최근 3개월 vs 6개월 전 3개월 ㎡당가 중위값 변화
  (2) 분기 지수(history.py, 백피팅) 6개월 변화 — 엔진과 방법이 달라 교차 확인용(타입·층 효과 추정에 미래 거래가 일부 쓰이는 점은 한계)
정답 라벨이 없으므로 '하락장에서 하락을, 상승장에서 상승을 내는가'와 '다른 방법과 방향이 맞는가'를 본다. 정확도 증명은 아니다.
  python3 tools/validate_downturn.py"""
import gzip, json, statistics as st, sys, zlib
from datetime import date
from pathlib import Path
ROOT = Path(__file__).parent.parent; sys.path.insert(0, str(ROOT))
import build_data as bd, history as hs
comps = [c for c in json.load(gzip.open(ROOT / "data" / "complex_trades.json.gz", "rt", encoding="utf-8")) if c["sgg"] < 20000]
cid = lambda c: format(zlib.crc32(f"{c['sgg']}|{c['umd']}|{c['name']}|{c['by']}".encode()) & 0xffffffff, "08x")
NQ = hs.qidx(date(2026, 8, 31).toordinal()) + 1
IDXS = {cid(c): hs.index_series(c["t"], NQ) for c in comps}; BY = {cid(c): c for c in comps}
def naive(ts, end):
    e = end.toordinal(); win = lambda a, b: [x[1] / x[2] for x in ts if a <= e - x[0] < b]; cur, old = win(0, 92), win(182, 274)
    return st.median(cur) / st.median(old) - 1 if len(cur) >= 4 and len(old) >= 4 else None
def qchg(i, end):
    r = IDXS.get(i)
    if not r: return None
    q = hs.qidx(end.toordinal()); a, b = r[1][q], r[1][q - 2] if q >= 2 else None
    return a / b - 1 if a and b else None
ENDS = sorted([date(2019, 6, 30), date(2020, 6, 30), date(2024, 12, 31), date(2025, 12, 31), date(2018, 6, 30), date(2019, 12, 31), date(2020, 12, 31), date(2021, 6, 30), date(2021, 12, 31), date(2022, 6, 30), date(2022, 9, 30), date(2022, 12, 31), date(2023, 3, 31), date(2023, 9, 30), date(2024, 6, 30), date(2025, 6, 30)])
print(f"{'기준일':10s} {'단지':>5s} {'상승':>5s} {'주춤':>5s} {'하락':>5s} {'확실하락':>6s} {'엔진중위':>8s} | {'지수중위':>8s} {'엔진-지수 상관':>12s} {'지수≤-3%':>8s}→{'엔진 하락 재현':>10s} {'단순≤-3%':>8s}→{'엔진 하락 재현':>10s}")
for end in ENDS:
    recs, _ = bd.build(end); recs = sorted((r for r, _ in recs if r["sgg"] < 20000 and r["trend"] and r["trend"]["w"] == 24), key=lambda r: 0)
    if not recs: print(end, "단지 없음"); continue
    cnt = {k: sum(1 for r in recs if r["trend"]["s"] == k) for k in ("상승", "주춤", "하락")}; sure = sum(1 for r in recs if r["trend"]["s"] == "하락" and r["trend"]["sure"])
    pi = [(r["trend"]["r"], qchg(r["id"], end), naive(BY[r["id"]]["t"], end) if r["id"] in BY else None) for r in recs]
    pq = [(a, b) for a, b, _ in pi if b is not None]; pn = [(a, c) for a, _, c in pi if c is not None]
    def corr(p):
        if len(p) < 20: return float("nan")
        mu, mv = st.mean(a for a, _ in p), st.mean(b for _, b in p); n = sum((a - mu) * (b - mv) for a, b in p); d = (sum((a - mu) ** 2 for a, _ in p) * sum((b - mv) ** 2 for _, b in p)) ** .5; return n / d if d else float("nan")
    def rec(p):
        t = [(a, b) for a, b in p if b <= -.03]; return (f"{sum(1 for a, _ in t if a <= -.03) / len(t):.0%}({len(t)})" if t else "-")
    print(f"{end}  {len(recs):5d} {cnt['상승']:5d} {cnt['주춤']:5d} {cnt['하락']:5d} {sure:6d} {st.median(r['trend']['r'] for r in recs):+8.1%} | {st.median(b for _, b in pq):+8.1%} {corr(pq):12.2f} {rec(pq):>20s} {rec(pn):>20s}")
