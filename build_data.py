"""data/complex_trades.json.gz → site/data/index.json, site/data/c/<id>.json
엔진(docs/service-requirements-v2.md §12에서 검증): 단지별로 최근 24개월 거래에 대해
  ln(㎡당 단가) ~ 상수 + 시간(월) + 층대(저/중/고 3등분) + 타입(전용면적 군집) 을 최소제곱으로 적합하고,
  시간 계수 ×6 = 6개월 추세. 표준오차에 1.2를 곱해(부트스트랩 대비 보수 보정) 90% 범위를 만든다.
  상태: 6개월 추세 ≥ +3% 상승, ≤ −3% 하락, 그 외 주춤. 90% 범위가 임계를 넘으면 '확실', 아니면 '추정'.
  python3 build_data.py [기준일 YYYY-MM-DD]   (기본: 오늘 기준 두 달 전 월말 = 신고 지연을 감안한 확정 구간 끝)"""
import gzip, json, math, statistics as st, sys, zlib
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).parent
OUT = ROOT / "site" / "data"
TAU, INFL, MONTHS, MIN_N, Z = 0.03, 1.2, 24, 20, 1.645
RECENT_MIN = 2                                                                 # 꺾임 모델에 필요한 최근 3개월 거래 수(미만이면 마지막 거래 이후를 외삽해 계수가 극단값으로 튀어 '참고용' 처리)
FALLBACK = 36


def month_end(y, m): return date(y + (m == 12), m % 12 + 1, 1) - timedelta(days=1)


def default_end():
    t = date.today(); y, m = (t.year, t.month - 2) if t.month > 2 else (t.year - 1, t.month + 10)
    return month_end(y, m)


def solve_inv(A):
    n = len(A); M = [row[:] + [1.0 if i == j else 0.0 for j in range(n)] for i, row in enumerate(A)]
    for i in range(n):
        p = max(range(i, n), key=lambda r: abs(M[r][i]))
        if abs(M[p][i]) < 1e-12: return None
        M[i], M[p] = M[p], M[i]; d = M[i][i]; M[i] = [x / d for x in M[i]]
        for r in range(n):
            if r != i:
                f = M[r][i]; M[r] = [a - f * b for a, b in zip(M[r], M[i])]
    return [row[n:] for row in M]


def design(ts, end, months=MONTHS, hinge=False, minn=MIN_N):
    """ts = [[ordinal, 금액(만원), 전용㎡, 층]]. 최근 months개월 윈도우로 설계행렬을 만든다.
    hinge=True 면 '최근 6개월 기울기 변화' 열(max(0, t+6))을 시간 열 바로 뒤에 추가한다(방향 전환을 빨리 잡기 위함)."""
    e = end.toordinal(); w = [x for x in ts if 0 <= e - x[0] < months * 30.4]
    if len(w) < minn: return None
    fl = sorted(x[3] for x in w); c1, c2 = fl[len(fl) // 3], fl[2 * len(fl) // 3]
    tiers = c1 < c2
    ar = sorted({round(x[2]) for x in w})
    X, y = [], []
    for x in w:
        t = (x[0] - e) / 30.4; row = [1.0, t] + ([max(0.0, t + 6)] if hinge else [])
        if tiers: row += [1.0 if c1 <= x[3] < c2 else 0.0, 1.0 if x[3] >= c2 else 0.0]
        row += [1.0 if round(x[2]) == a else 0.0 for a in ar[1:]]
        X.append(row); y.append(math.log(x[1] / x[2]))
    n, k = len(X), len(X[0])
    if n - k < 8: return None
    inv = solve_inv([[sum(X[r][i] * X[r][j] for r in range(n)) for j in range(k)] for i in range(k)])
    if inv is None: return None
    Xty = [sum(X[r][i] * y[r] for r in range(n)) for i in range(k)]
    beta = [sum(inv[i][j] * Xty[j] for j in range(k)) for i in range(k)]
    s2 = sum((y[r] - sum(beta[i] * X[r][i] for i in range(k))) ** 2 for r in range(n)) / (n - k)
    return dict(w=w, tiers=tiers, c1=c1, c2=c2, ar=ar, beta=beta, inv=inv, s2=s2, n=n, k=k, hinge=hinge)


def six(d):
    """설계 d 의 6개월 변화(로그)와 표준오차(×INFL). hinge 모델이면 최근 6개월 기울기 = 시간계수 + 꺾임계수."""
    i = d["inv"]; b = d["beta"]
    if d["hinge"]: return 6 * (b[1] + b[2]), 6 * math.sqrt(d["s2"] * (i[1][1] + i[2][2] + 2 * i[1][2])) * INFL
    return 6 * b[1], 6 * math.sqrt(d["s2"] * i[1][1]) * INFL


def xvec(d, t, a, tier):
    row = [1.0, t]
    if d["tiers"]: row += [1.0 if tier == 1 else 0.0, 1.0 if tier == 2 else 0.0]
    return row + [1.0 if a == v else 0.0 for v in d["ar"][1:]]


def quad(inv, x): return sum(x[i] * inv[i][j] * x[j] for i in range(len(x)) for j in range(len(x)))


def status(r6, se6):
    r = math.exp(r6) - 1; lo, hi = math.exp(r6 - Z * se6) - 1, math.exp(r6 + Z * se6) - 1
    s = "상승" if r >= TAU else "하락" if r <= -TAU else "주춤"
    sure = lo >= TAU if s == "상승" else hi <= -TAU if s == "하락" else (lo > -TAU and hi < TAU)
    return s, bool(sure), r, lo, hi


def build(end, src=None):
    comps = json.load(gzip.open(src or ROOT / "data" / "complex_trades.json.gz", "rt", encoding="utf-8"))
    e = end.toordinal(); last_day = max(x[0] for c in comps for x in c["t"])
    recs, ids = [], set()
    for c in comps:
        key = f"{c['sgg']}|{c['umd']}|{c['name']}|{c['by']}"; cid = format(zlib.crc32(key.encode()) & 0xffffffff, "08x")
        assert cid not in ids, "id 충돌"; ids.add(cid)
        ts = c["t"]; d = design(ts, end); win = MONTHS
        if not d: d = design(ts, end, FALLBACK); win = FALLBACK                    # 24개월 표본 부족 → 36개월 창(보조, 항상 '추정')
        rec = dict(id=cid, name=c["name"], reg=c["reg"], gu=c["gu"], umd=c["umd"], by=c["by"], sgg=c["sgg"], n=len(ts),
                   n12=sum(1 for x in ts if 0 <= e - x[0] < 365), last=last_day - max(x[0] for x in ts), trend=None)
        det = dict(types=[], tiers=None, est={}, est_kind=None, series=None, recent=sorted(ts, key=lambda x: -x[0])[:12], scatter=[])
        if d:
            r6, se6 = six(d); mode = "A"; extra = {}
            if win == MONTHS:                                                          # 최근 속도(꺾임 24개월)와 12개월 선형의 평균: 전환점에서 24개월 직선보다 훨씬 빨리 반응(validate_downturn.py)
                db, dc = design(ts, end, MONTHS, True), design(ts, end, 12, False, 12)
                if db and dc and sum(1 for x in ts if 0 <= e - x[0] < 3 * 30.4) >= RECENT_MIN:
                    (rb, seb), (rc, sec) = six(db), six(dc); r6, se6, mode = (rb + rc) / 2, max(seb, sec), "E"
                    extra = dict(a=round(math.exp(six(d)[0]) - 1, 4), b=round(math.exp(rb) - 1, 4), c=round(math.exp(rc) - 1, 4))
            s, sure, r, lo, hi = status(r6, se6)
            rec["trend"] = dict(r=round(r, 4), lo=round(lo, 4), hi=round(hi, 4), s=s, sure=sure and mode == "E" and win == MONTHS, n=d["n"], w=win, m=mode, **extra)
            w = d["w"]; det["scatter"] = [[x[0] - e, x[1], round(x[2]), x[3]] for x in w]
            cnt = {a: [x for x in w if round(x[2]) == a] for a in d["ar"]}
            det["types"] = [dict(a=a, n=len(v), m=round(st.mean(x[2] for x in v), 2)) for a, v in sorted(cnt.items(), key=lambda kv: -len(kv[1])) if len(v) >= 3]
            det["tiers"] = [d["c1"], d["c2"]] if d["tiers"] else None
            det["est_kind"] = "regression"
            for tp in det["types"]:
                for tier in (range(3) if d["tiers"] else [0]):
                    x = xvec(d, 0.0, tp["a"], tier); mu = sum(b * v for b, v in zip(d["beta"], x)); q = quad(d["inv"], x)
                    sd = math.sqrt(d["s2"] * (1 + q))                                  # 개별 거래가 들어갈 범위(예측 구간)
                    det["est"][f"{tp['a']}|{tier}"] = [round(math.exp(mu) * tp["m"]), round(math.exp(mu - Z * sd) * tp["m"]), round(math.exp(mu + Z * sd) * tp["m"])]
            if det["types"]:
                ref = det["types"][0]["a"]; tier = 1 if d["tiers"] else 0; ser = []
                for mth in range(-MONTHS, 1):
                    x = xvec(d, float(mth), ref, tier); mu = sum(b * v for b, v in zip(d["beta"], x)); sdm = math.sqrt(d["s2"] * quad(d["inv"], x)) * INFL
                    ser.append([mth, round(math.exp(mu), 1), round(math.exp(mu - Z * sdm), 1), round(math.exp(mu + Z * sdm), 1)])
                det["series"] = dict(ref=ref, tier=tier, pts=ser)
        else:                                                                         # 추세 불가: 최근 12개월 거래 중위값으로 대체(보정 없음)
            yr = [x for x in ts if 0 <= e - x[0] < 365]
            by = {}
            for x in yr: by.setdefault(round(x[2]), []).append(x)
            det["types"] = [dict(a=a, n=len(v), m=round(st.mean(x[2] for x in v), 2)) for a, v in sorted(by.items(), key=lambda kv: -len(kv[1])) if len(v) >= 3]
            for tp in det["types"]:
                v = sorted(x[1] for x in by[tp["a"]]); q = lambda p: v[min(len(v) - 1, int(p * len(v)))]
                det["est"][f"{tp['a']}|0"] = [round(st.median(v)), q(.1), q(.9)]
            det["est_kind"] = "median" if det["types"] else None
        ok = [t for t in det["types"] if t["n"] >= 5] or det["types"]                  # 예시 후보 선정용: 84㎡ 안팎 평형의 중간층 시세
        if ok:
            pa = min(ok, key=lambda t: abs(t["a"] - 90))["a"]; pe = det["est"].get(f"{pa}|{1 if det['tiers'] else 0}")
            if pe: rec["pa"], rec["px"] = pa, pe[0]
        recs.append((rec, det))
    # 주변 입지: 같은 동·같은 구(시)에서 추세를 낸 단지들의 6개월 추세 중위값
    for key in ("umd", "sgg"):
        g = {}
        for rec, _ in recs:
            if rec["trend"] and rec["trend"]["m"] == "E": g.setdefault((rec["sgg"], rec["umd"]) if key == "umd" else rec["sgg"], []).append(rec["trend"]["r"])
        for rec, _ in recs:
            gk = (rec["sgg"], rec["umd"]) if key == "umd" else rec["sgg"]
            v = g.get(gk, []); rec["dong" if key == "umd" else "guagg"] = None
            if rec["trend"] and rec["trend"]["m"] == "E" and len(v) >= 6:                  # 최근 변화를 반영한 단지끼리만 비교(참고용 단지는 제외)
                rank = 1 + sum(1 for x in v if x > rec["trend"]["r"])
                rec["dong" if key == "umd" else "guagg"] = dict(med=round(st.median(v), 4), n=len(v), rank=rank)
    first_day = min(x[0] for c in comps for x in c["t"])
    return recs, dict(end=end.isoformat(), end_ord=e, first_day=first_day, last_day=last_day, generated=date.today().isoformat(), n=len(recs))


def write(recs, meta):
    (OUT / "c").mkdir(parents=True, exist_ok=True)
    for rec, det in recs:
        (OUT / "c" / f"{rec['id']}.json").write_text(json.dumps(det, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    cand = {}                                                                    # 조건으로 찾기용: 평형별 [전용, 표본수, 평균전용, 중간층 추정시세 mid, lo, hi]
    for rec, det in recs:
        if rec["n12"] < 12: continue
        rows = []
        for tp in det["types"]:
            if tp["n"] < 5: continue
            e = det["est"].get(f"{tp['a']}|{1 if det['tiers'] else 0}")
            if e: rows.append([tp["a"], tp["n"], tp["m"], e[0], e[1], e[2]])
        if rows: cand[rec["id"]] = rows
    (OUT / "cand.json").write_text(json.dumps(cand, ensure_ascii=False, separators=(",", ":"), allow_nan=False), encoding="utf-8")
    (OUT / "index.json").write_text(json.dumps(dict(meta=meta, c=[r for r, _ in recs]), ensure_ascii=False, separators=(",", ":"), allow_nan=False), encoding="utf-8")


if __name__ == "__main__":
    end = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else default_end()
    recs, meta = build(end); write(recs, meta)
    tr = [r for r, _ in recs if r["trend"]]; import collections
    c = collections.Counter(r["trend"]["s"] for r in tr)
    print(f"기준일 {end}: 단지 {len(recs):,}개, 추세 산출 {len(tr):,}개({len(tr)/len(recs):.0%}) — " + ", ".join(f"{k} {v}" for k, v in c.items()))
