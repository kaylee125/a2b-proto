"""입지(구·시, 동) 단위 가격 추이와 환금성 → site/data/area.json
가격 추이: 입지 안 단지들의 분기 가격(hist.json 의 단지 지수)을 '단지 고정효과 + 분기효과' 패널로 합쳐 입지 지수를 만든다(백피팅).
  단지마다 가격 수준이 달라도 같은 단지의 분기 변화만으로 입지 흐름을 잡는다. 분기마다 관측 단지(2분기 이상 값이 있는 단지)가 MIN_C 미만이면 그 분기는 비운다.
환금성: 입지 안 모든 단지의 신고 거래 건수(분기·12개월·전년 대비·10년 평균 대비·단지당)와 하락기 거래 감소.
키: 구·시 = "11350", 동 = "11350:월계동" (조건으로 후보 찾기의 입지 키와 같다).
  python3 history.py && python3 area.py [기준일 YYYY-MM-DD]"""
import gzip, json, math, statistics as st, sys, zlib
from datetime import date
import build_data as bd, history as hs

MIN_C = 5                                                                      # 분기 지수를 내려면 필요한 관측 단지 수
ITER = 40


def panel_index(series, nq):
    """series=[[분기 가격|None]...] → (분기 지수 리스트(첫 유효 분기=100)|None, 지수에 쓰인 단지 수)"""
    series = [p for p in series if sum(v is not None for v in p) >= 2]
    n = [0] * nq
    for p in series:
        for q, v in enumerate(p):
            if v: n[q] += 1
    ok = [n[q] >= MIN_C for q in range(nq)]
    obs = [(c, q, math.log(v)) for c, p in enumerate(series) for q, v in enumerate(p) if v and ok[q]]
    if not obs: return None, len(series)
    te, ce = [0.0] * nq, [0.0] * len(series)
    for _ in range(ITER):
        s, k = [0.0] * nq, [0] * nq
        for c, q, y in obs: s[q] += y - ce[c]; k[q] += 1
        te = [s[q] / k[q] if k[q] else 0.0 for q in range(nq)]
        s, k = [0.0] * len(series), [0] * len(series)
        for c, q, y in obs: s[c] += y - te[q]; k[c] += 1
        ce = [s[c] / k[c] if k[c] else 0.0 for c in range(len(series))]
    f = next(q for q in range(nq) if ok[q])
    return [round(100 * math.exp(te[q] - te[f]), 1) if ok[q] else None for q in range(nq)], len(series)


def vol_drop(cnt):
    """분기 거래량(2분기 평균)의 하락기 변화: 2020Q4~2022Q4 고점 → 이후 2024Q2까지 저점. [고점분기, 저점분기, 변화율]|None"""
    a, b, c = hs.qidx(date(2020, 10, 1).toordinal()), hs.qidx(date(2022, 12, 31).toordinal()), hs.qidx(date(2024, 6, 30).toordinal())
    s = hs.smooth(cnt); win = [(i, s[i]) for i in range(a, min(c + 1, len(s))) if s[i] is not None]
    pk = [(i, v) for i, v in win if i <= b]
    if not pk: return None
    pi, pv = max(pk, key=lambda x: x[1])
    after = [(i, v) for i, v in win if i > pi]
    if pv < 6 or not after: return None                                        # 고점 거래량이 너무 작으면 비율이 의미 없음
    ti, tv = min(after, key=lambda x: x[1])
    return [hs.qname(pi), hs.qname(ti), round(min(tv, pv) / pv - 1, 4)]


def lastq(p):
    return next((i for i in range(len(p) - 1, -1, -1) if p[i] is not None), -1)


def build(end, comps=None, H=None):
    comps = comps or json.load(gzip.open(bd.ROOT / "data" / "complex_trades.json.gz", "rt", encoding="utf-8"))
    H = H or json.load(open(bd.OUT / "hist.json", encoding="utf-8"))
    nq, e = H["n"], end.toordinal(); first = min(x[0] for c in comps for x in c["t"])
    areas = {}
    def A(key, name, sgg):
        return areas.setdefault(key, dict(name=name, sgg=sgg, nc=0, ser=[], cnt=[0] * nq, t12=0, t12p=0, t3=0, tot=0, act=0, pp=[]))
    for c in comps:
        cid = format(zlib.crc32(f"{c['sgg']}|{c['umd']}|{c['name']}|{c['by']}".encode()) & 0xffffffff, "08x")
        hp = H["c"].get(cid)
        n12 = 0
        for key, name in ((str(c["sgg"]), c["gu"]), (f"{c['sgg']}:{c['umd']}", c["umd"])):
            a = A(key, name, c["sgg"]); a["nc"] += 1
            if hp: a["ser"].append(hp["p"])
        for x in c["t"]:
            if x[0] > e: continue
            q, age = hs.qidx(x[0]), e - x[0]
            for key in (str(c["sgg"]), f"{c['sgg']}:{c['umd']}"):
                a = areas[key]
                if 0 <= q < nq: a["cnt"][q] += 1
                a["tot"] += 1
                if age < 365: a["t12"] += 1; a["pp"].append(x[1] / x[2])
                elif age < 730: a["t12p"] += 1
                if age < 91: a["t3"] += 1
            if e - x[0] < 365: n12 += 1
        if n12:
            for key in (str(c["sgg"]), f"{c['sgg']}:{c['umd']}"): areas[key]["act"] += 1
    years = (e - first) / 365.25
    out = {}
    for key, a in areas.items():
        idx, ni = panel_index(a["ser"], nq)
        r = dict(name=a["name"], sgg=a["sgg"], nc=a["nc"], ni=ni, cnt=a["cnt"], t12=a["t12"], t12p=a["t12p"], t3=a["t3"], act=a["act"],
                 per12=round(a["t12"] / a["nc"], 1), avg10=round(a["tot"] / years, 1), px84=round(st.median(a["pp"]) * 84) if len(a["pp"]) >= 10 else None)
        r["vd"] = vol_drop(a["cnt"])
        if idx:
            l = lastq(idx); r["idx"] = idx
            r["ch"] = [round(idx[l] / idx[l - k] - 1, 4) if l - k >= 0 and idx[l - k] else None for k in (2, 4)] + [round(idx[l] / max(v for v in idx if v) - 1, 4)]
            r["dd"] = hs.defense(idx)
        else: r["idx"] = None
        out[key] = r
    for level in (lambda k: ":" not in k, lambda k: ":" in k):                 # 같은 층위(구·시끼리, 동끼리) 안의 순위: 12개월 변화, 단지당 거래
        ks = [k for k in out if level(k) and out[k]["nc"] >= 3]
        for fld, val in (("rk12", lambda r: (r.get("ch") or [None, None])[1]), ("rkliq", lambda r: r["per12"])):
            v = sorted((k for k in ks if val(out[k]) is not None), key=lambda k: -val(out[k]))
            for i, k in enumerate(v): out[k][fld] = [i + 1, len(v)]
    return dict(meta=dict(q0=H["q0"], n=nq, end=end.isoformat(), min_c=MIN_C), a=out)


if __name__ == "__main__":
    end = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else bd.default_end()
    H = json.load(open(bd.OUT / "hist.json", encoding="utf-8"))
    res = build(end, H=H); path = bd.OUT / "area.json"
    path.write_text(json.dumps(res, ensure_ascii=False, separators=(",", ":"), allow_nan=False), encoding="utf-8")
    a = res["a"]; g = [k for k in a if ":" not in k]; d = [k for k in a if ":" in k]
    print(f"구·시 {len(g)}개(지수 {sum(1 for k in g if a[k]['idx'])}), 동 {len(d)}개(지수 {sum(1 for k in d if a[k]['idx'])}) → {path} ({path.stat().st_size/1e6:.2f}MB)")
