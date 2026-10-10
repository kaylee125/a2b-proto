"""단지별 10년 분기 지수 + 하락기 방어력 → site/data/hist.json
지수: ln(㎡당가) = 분기효과 + 평형효과 + 층대효과 (백피팅 5회). 같은 단지 안에서 평형·층 구성이 달라져도 분기 가격이 덜 흔들린다.
한 분기에 거래가 3건 미만이면 그 분기는 비워 둔다(null).
방어력: 2020Q4~2022Q4 고점(2분기 평균) → 이후 2024Q2까지 저점 → 낙폭, 고점 회복까지 걸린 분기 수(고점 이후 하락이 없으면 낙폭 0).
  python3 history.py [기준일 YYYY-MM-DD]"""
import gzip, json, math, statistics as st, sys
from datetime import date
from pathlib import Path
import build_data as bd

Q0 = (2016, 4)                                       # 첫 분기 2016Q4
MIN_Q = 3


def qidx(o):
    d = date.fromordinal(o); return (d.year - Q0[0]) * 4 + (d.month - 1) // 3 - (Q0[1] - 1)


def qname(i):
    t = Q0[0] * 4 + Q0[1] - 1 + i; return f"{t // 4}Q{t % 4 + 1}"


def index_series(ts, nq):
    """ts=[[ordinal,금액,전용㎡,층]] → (기준평형, 분기별 가격(만원)|None 리스트). 거래가 너무 적으면 None."""
    if len(ts) < 12: return None
    fl = sorted(x[3] for x in ts); c1, c2 = fl[len(fl) // 3], fl[2 * len(fl) // 3]
    rows = [(qidx(x[0]), round(x[2]), (0 if x[3] < c1 else 1 if x[3] < c2 else 2) if c1 < c2 else 0, math.log(x[1] / x[2]), x[2]) for x in ts]
    rows = [r for r in rows if 0 <= r[0] < nq]
    if len(rows) < 12: return None
    cnt = {}
    for r in rows: cnt[r[1]] = cnt.get(r[1], 0) + 1
    ref = max(cnt, key=cnt.get); ma = st.mean(r[4] for r in rows if r[1] == ref)
    qe, te, fe = [0.0] * nq, {}, [0.0, 0.0, 0.0]
    for _ in range(5):                                                         # 백피팅
        s = {}; [s.setdefault(r[0], []).append(r[3] - te.get(r[1], 0) - fe[r[2]]) for r in rows]; qe = [st.mean(s[q]) if q in s else 0.0 for q in range(nq)]
        s = {}; [s.setdefault(r[1], []).append(r[3] - qe[r[0]] - fe[r[2]]) for r in rows]; te = {a: st.mean(v) for a, v in s.items()}
        s = {}; [s.setdefault(r[2], []).append(r[3] - qe[r[0]] - te[r[1]]) for r in rows]; fe = [st.mean(s[k]) if k in s else 0.0 for k in range(3)]
        sh = te[ref]; te = {a: v - sh for a, v in te.items()}; qe = [v + sh for v in qe]
        f1 = fe[1]; fe = [v - f1 for v in fe]; qe = [v + f1 for v in qe]
    n = [0] * nq
    for r in rows: n[r[0]] += 1
    return ref, [round(math.exp(qe[q]) * ma, 0) if n[q] >= MIN_Q else None for q in range(nq)]


def smooth(p):                                                                 # 2분기 평균(둘 중 하나만 있으면 그 값)
    out = []
    for i, v in enumerate(p):
        w = [x for x in (p[i - 1] if i else None, v) if x is not None]; out.append(sum(w) / len(w) if v is not None and w else None)
    return out


def defense(p):
    """p=분기 가격 리스트 → [고점분기, 저점분기, 낙폭, 회복분기수|None] 또는 None"""
    a, b, c = qidx(date(2020, 10, 1).toordinal()), qidx(date(2022, 12, 31).toordinal()), qidx(date(2024, 6, 30).toordinal())
    s = smooth(p); win = [(i, s[i]) for i in range(a, min(c + 1, len(s))) if s[i] is not None]
    if sum(1 for i, _ in win if i <= b) < 4 or sum(1 for i, _ in win if i > b) < 3: return None
    pi, pv = max(((i, v) for i, v in win if i <= b), key=lambda x: x[1])
    after = [(i, v) for i, v in win if i > pi]
    if not after: return None
    ti, tv = min(after, key=lambda x: x[1])
    if tv >= pv: return [qname(pi), qname(pi), 0.0, 0]                           # 고점 이후 더 낮아진 적이 없음 → 하락 없음
    rec = next((i - ti for i in range(ti + 1, len(s)) if s[i] is not None and s[i] >= pv), None)
    return [qname(pi), qname(ti), round(tv / pv - 1, 4), rec]


def build(end, comps=None):
    comps = comps or json.load(gzip.open(bd.ROOT / "data" / "complex_trades.json.gz", "rt", encoding="utf-8"))
    nq = qidx(end.toordinal()) + 1; out, dd = {}, {}
    for c in comps:
        key = f"{c['sgg']}|{c['umd']}|{c['name']}|{c['by']}"; cid = format(__import__("zlib").crc32(key.encode()) & 0xffffffff, "08x")
        r = index_series(c["t"], nq)
        if r:
            ref, p = r
            if sum(v is not None for v in p) >= 8: out[cid] = dict(ref=ref, p=p, d=defense(p), gu=c["gu"])
    by = {}
    for v in out.values():
        if v["d"]: by.setdefault(v["gu"], []).append(v["d"][2])
    gu = {g: dict(med=round(st.median(x), 4), n=len(x)) for g, x in by.items() if len(x) >= 5}
    return dict(q0=qname(0), n=nq, gu=gu, c=out)


if __name__ == "__main__":
    end = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else bd.default_end()
    h = build(end); path = bd.OUT / "hist.json"
    path.write_text(json.dumps(h, ensure_ascii=False, separators=(",", ":"), allow_nan=False), encoding="utf-8")
    dds = [v["d"][2] for v in h["c"].values() if v["d"]]
    print(f"분기 {h['n']}개({h['q0']}~), 지수 단지 {len(h['c']):,}개, 방어력 산출 {len(dds):,}개, 낙폭 중위 {st.median(dds):+.1%} → {path} ({path.stat().st_size/1e6:.1f}MB)")
