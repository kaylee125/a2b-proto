"""데이터 빌드 검증: (1) 이전 분석(docs §12)의 숫자 재현 (2) 회귀 해를 독립 방식(유리수 연산)으로 재계산 (3) 산출물 무결성."""
import json
import math
from datetime import date
from fractions import Fraction
from pathlib import Path

import pytest

import build_data as bd

END = date(2026, 8, 31)
RECS, META = bd.build(END)
COMPS = json.load(__import__('gzip').open(bd.ROOT / 'data' / 'complex_trades.json.gz', 'rt', encoding='utf-8'))
R = {r["id"]: (r, d) for r, d in RECS}
MINE = next(r for r, _ in RECS if r["sgg"] == 41360 and "한양수자인리버파크" in r["name"])


def test_current_numbers_and_old_linear_model_still_reproduced():
    assert len(RECS) == 6251 and sum(1 for r, _ in RECS if r["trend"]) == 3156
    E = [r for r, _ in RECS if r["trend"] and r["trend"]["m"] == "E"]
    assert len(E) == 2141 and sum(1 for r in E if r["trend"]["sure"]) == 1142
    assert {k: sum(1 for r in E if r["trend"]["s"] == k) for k in ("상승", "주춤", "하락")} == {"상승": 1814, "주춤": 224, "하락": 103}
    assert sum(1 for r, _ in RECS if r["trend"] and r["trend"]["m"] != "E") == 1015
    # 24개월 선형 모델(2,725개: 상승 2187·주춤 534·하락 4)은 그대로 재현되어야 함(서울·구리·하남·다산만일 때 1,958개: 상승 1646·주춤 310·하락 2)
    lin = {"상승": 0, "주춤": 0, "하락": 0}; n = 0
    for c in COMPS:
        d = bd.design(c["t"], END)
        if d: n += 1; lin[bd.status(*bd.six(d))[0]] += 1
    assert n == 2725 and lin == {"상승": 2187, "주춤": 534, "하락": 4}
    t = MINE["trend"]
    assert (t["s"], t["sure"], t["m"]) == ("상승", False, "E")
    assert t["r"] == pytest.approx(0.0641, abs=0.0005) and t["lo"] == pytest.approx(0.0045, abs=0.0005) and t["hi"] == pytest.approx(0.1272, abs=0.0005)
    assert (t["a"], t["b"], t["c"]) == (pytest.approx(0.0175, abs=0.0005), pytest.approx(0.0956, abs=0.0005), pytest.approx(0.0334, abs=0.0005))
    assert MINE["dong"]["n"] == 38 and MINE["dong"]["med"] == pytest.approx(0.1213, abs=0.0005) and MINE["dong"]["rank"] == 35


def exact_time_coefs(d, end, hinge):
    """같은 설계행렬을 분수(유리수) 가우스-조던으로 풀어 시간 계수(와 꺾임 계수)를 반환."""
    e = end.toordinal(); X, y = [], []
    for x in d["w"]:
        t = Fraction(int(round((x[0] - e) / 30.4 * 1e9)), 10 ** 9); row = [Fraction(1), t] + ([max(Fraction(0), t + 6)] if hinge else [])
        if d["tiers"]: row += [Fraction(int(d["c1"] <= x[3] < d["c2"])), Fraction(int(x[3] >= d["c2"]))]
        row += [Fraction(int(round(x[2]) == a)) for a in d["ar"][1:]]; X.append(row); y.append(Fraction(math.log(x[1] / x[2])))
    k = len(X[0]); A = [[sum(X[r][i] * X[r][j] for r in range(len(X))) for j in range(k)] + [sum(X[r][i] * y[r] for r in range(len(X)))] for i in range(k)]
    for i in range(k):
        p = next(r for r in range(i, k) if A[r][i] != 0); A[i], A[p] = A[p], A[i]; piv = A[i][i]; A[i] = [v / piv for v in A[i]]
        for r in range(k):
            if r != i: f = A[r][i]; A[r] = [a - f * b for a, b in zip(A[r], A[i])]
    return [float(A[i][k]) for i in range(k)]


def test_regression_matches_independent_exact_solver_for_all_three_models():
    c = next(x for x in COMPS if x["sgg"] == 41360 and "한양수자인리버파크" in x["name"])
    for months, hinge, minn in ((24, False, 20), (24, True, 20), (12, False, 12)):
        d = bd.design(c["t"], END, months, hinge, minn); b = exact_time_coefs(d, END, hinge)
        assert b[1] == pytest.approx(d["beta"][1], abs=1e-9)
        if hinge: assert b[2] == pytest.approx(d["beta"][2], abs=1e-9) and 6 * (b[1] + b[2]) == pytest.approx(bd.six(d)[0], abs=1e-8)


def test_labels_follow_the_rule_and_ranges_are_ordered():
    for r, d in RECS:
        t = r["trend"]
        if t:
            assert t["lo"] <= t["r"] <= t["hi"]
            near = abs(abs(t["r"]) - 0.03) <= 0.00005                          # 저장값이 소수 4자리 반올림이라 임계 경계에서만 허용
            if not near: assert t["s"] == ("상승" if t["r"] >= 0.03 else "하락" if t["r"] <= -0.03 else "주춤")
            near_s = min(abs(abs(t[k]) - 0.03) for k in ("lo", "hi")) <= 0.00005
            if t["sure"] and not near_s:
                assert (t["lo"] >= 0.03) if t["s"] == "상승" else (t["hi"] <= -0.03) if t["s"] == "하락" else (t["lo"] > -0.03 and t["hi"] < 0.03)
        for key, (mid, lo, hi) in d["est"].items():
            assert 0 < lo <= mid <= hi, (r["name"], key)
        if d["series"]:
            assert len(d["series"]["pts"]) == 25 and all(p[2] <= p[1] <= p[3] for p in d["series"]["pts"])


def test_peer_stats_need_six_complexes_and_ids_unique():
    assert len({r["id"] for r, _ in RECS}) == len(RECS)
    for r, _ in RECS:
        if r["dong"]: assert r["dong"]["n"] >= 6 and 1 <= r["dong"]["rank"] <= r["dong"]["n"] and r["trend"]


def test_written_files_are_complete_and_clean():
    p = bd.ROOT / "site" / "data"
    idx = json.loads((p / "index.json").read_text(encoding="utf-8"))
    assert idx["meta"]["end"] == "2026-08-31" and len(idx["c"]) == 6251 and idx["meta"]["first_day"] < idx["meta"]["last_day"]
    assert all((p / "c" / f"{c['id']}.json").exists() for c in idx["c"][:50]) and len(list((p / "c").glob("*.json"))) == 6251
    assert "NaN" not in (p / "index.json").read_text(encoding="utf-8")


def test_reference_only_trends_are_never_certain_and_not_compared():
    ref = [r for r, _ in RECS if r["trend"] and r["trend"]["m"] != "E"]
    assert len(ref) == 1015 and sum(1 for r in ref if r["trend"]["w"] == 36) == 431
    assert all(not r["trend"]["sure"] and r["dong"] is None and r["guagg"] is None for r in ref)
    for r in ref:                                                                    # 참고용은 '최근 12개월 12건 미만', '24개월 20건 미만' 또는 '최근 3개월 거래 부족'인 단지에만
        c = next(x for x in COMPS if x["sgg"] == r["sgg"] and x["umd"] == r["umd"] and x["name"] == r["name"] and x["by"] == r["by"])
        if r["trend"]["w"] == 24: assert bd.design(c["t"], END, 12, False, 12) is None or bd.design(c["t"], END, 24, True) is None or _recent(c) < bd.RECENT_MIN
        else: assert bd.design(c["t"], END) is None


def test_history_file_is_consistent_with_trades():
    h = json.loads((bd.ROOT / "site" / "data" / "hist.json").read_text(encoding="utf-8"))
    assert h["q0"] == "2016Q4" and h["n"] == 40 and len(h["c"]) > 2000
    ids = {r["id"] for r, _ in RECS}
    assert set(h["c"]) <= ids
    for v in h["c"].values():
        assert len(v["p"]) == 40 and sum(x is not None for x in v["p"]) >= 8 and all(x is None or x > 0 for x in v["p"])
        if v["d"]: assert v["d"][2] <= 0 and v["d"][0] <= v["d"][1] and (v["d"][3] is None or v["d"][3] >= (0 if v["d"][2] == 0 else 1))


def _recent(c): return sum(1 for x in c["t"] if 0 <= END.toordinal() - x[0] < 3 * 30.4)


def test_hinge_trend_needs_recent_trades():
    """꺾임(최근 속도) 모델은 마지막 거래 이후를 외삽하면 극단값이 나오므로 최근 3개월 거래가 있는 단지에만 쓴다(2026-10-09 검증에서 발견)."""
    E = {(r["sgg"], r["umd"], r["name"], r["by"]) for r, _ in RECS if r["trend"] and r["trend"]["m"] == "E"}
    assert E and all(_recent(c) >= bd.RECENT_MIN for c in COMPS if (c["sgg"], c["umd"], c["name"], c["by"]) in E)


# ---------- 입지(구·시, 동) 단위 가격 추이·환금성 (area.json) ----------
AREA = json.load(open(bd.OUT / "area.json", encoding="utf-8")); AA = AREA["a"]
HIST = json.load(open(bd.OUT / "hist.json", encoding="utf-8"))


def _cid(c): return format(__import__("zlib").crc32(f"{c['sgg']}|{c['umd']}|{c['name']}|{c['by']}".encode()) & 0xffffffff, "08x")


def _in(key, c): return str(c["sgg"]) == key or f"{c['sgg']}:{c['umd']}" == key


def test_area_trade_counts_match_raw_trades():
    """입지 거래 건수(분기 합·12개월·전년·최근 3개월)는 원본 거래를 직접 센 값과 같다. 구·시와 동 모두."""
    e = END.toordinal()
    for key in ("11350", "11680", "41360", "41135", "11350:월계동", "11680:대치동", "41360:다산동", "41597:청계동", "41430", "41430:내손동"):
        ts = [x for c in COMPS if _in(key, c) for x in c["t"] if x[0] <= e]; a = AA[key]
        assert sum(a["cnt"]) == len(ts), key
        assert a["t12"] == sum(1 for x in ts if e - x[0] < 365) and a["t12p"] == sum(1 for x in ts if 365 <= e - x[0] < 730) and a["t3"] == sum(1 for x in ts if e - x[0] < 91), key
        assert a["nc"] == sum(1 for c in COMPS if _in(key, c)), key


def test_area_hierarchy_is_consistent():
    """구·시 값은 그 안의 동 값을 합친 것과 같다(단지 수·거래 수·분기별 거래)."""
    for g in [k for k in AA if ":" not in k]:
        ds = [a for k, a in AA.items() if k.startswith(g + ":")]
        assert sum(a["nc"] for a in ds) == AA[g]["nc"] and sum(a["t12"] for a in ds) == AA[g]["t12"], g
        assert [sum(a["cnt"][q] for a in ds) for q in range(AREA["meta"]["n"])] == AA[g]["cnt"], g
    assert len([k for k in AA if ":" not in k]) == 36


def test_area_index_rules_and_min_sample():
    """지수는 첫 유효 분기가 100이고, 값이 있는 분기마다 2분기 이상 관측된 단지가 MIN_C개 이상이다."""
    nq, mc = AREA["meta"]["n"], AREA["meta"]["min_c"]
    by = {}
    for c in COMPS:
        hp = HIST["c"].get(_cid(c))
        if hp and sum(v is not None for v in hp["p"]) >= 2:
            for key in (str(c["sgg"]), f"{c['sgg']}:{c['umd']}"): by.setdefault(key, []).append(hp["p"])
    for key, a in AA.items():
        if not a["idx"]: continue
        v = [x for x in a["idx"] if x is not None]; assert v[0] == 100.0 and all(x > 0 for x in v), key
        for q in range(nq):
            n = sum(1 for p in by[key] if p[q] is not None)
            assert (a["idx"][q] is not None) == (n >= mc), (key, q, n)


def test_area_index_agrees_with_independent_median_changes():
    """독립 방법(인접 분기 단지별 가격 변화의 중위값)과 분기 변화율이 같은 방향으로 움직인다(상관 0.85 이상)."""
    import statistics
    nq = AREA["meta"]["n"]
    for key in ("11350", "11680", "41135", "41173", "11710", "41597"):
        ser = [HIST["c"][_cid(c)]["p"] for c in COMPS if _in(key, c) and _cid(c) in HIST["c"]]; idx = AA[key]["idx"]; pr = []
        for q in range(1, nq):
            d = [math.log(p[q] / p[q - 1]) for p in ser if p[q] and p[q - 1]]
            if len(d) >= 5 and idx[q] and idx[q - 1]: pr.append((math.log(idx[q] / idx[q - 1]), statistics.median(d)))
        ma, mb = sum(a for a, _ in pr) / len(pr), sum(b for _, b in pr) / len(pr)
        corr = sum((a - ma) * (b - mb) for a, b in pr) / math.sqrt(sum((a - ma) ** 2 for a, _ in pr) * sum((b - mb) ** 2 for _, b in pr))
        assert len(pr) >= 30 and corr > 0.85, (key, len(pr), corr)


# ---------- 배포(runlot) 제한 점검 ----------
def test_runlot_config_and_bundle_limits():
    """runlot 정적 배포 제한(문서 기준)을 넘지 않는다: 이름 규칙, 파일 수 2만, 압축 64MiB, 압축 해제 512MiB, 파일 64MiB, 숨김 파일·심볼릭 링크 없음."""
    import io, re, tarfile
    cfg = json.load(open(bd.ROOT / "runlot.json", encoding="utf-8"))
    assert re.fullmatch(r"[a-z0-9](-?[a-z0-9])*", cfg["name"]) and len(cfg["name"]) <= 30 and "main" not in cfg and cfg["assets"] == "site"
    root = (bd.ROOT / cfg["assets"]).resolve(); assert root.is_dir() and root.is_relative_to(bd.ROOT.resolve())
    every = list(root.rglob("*")); files = [f for f in every if f.is_file()]
    assert not [f for f in every if f.is_symlink() or f.name.startswith(".")], "숨김 파일·심볼릭 링크가 있으면 안 된다"
    assert len(files) <= 16000, f"파일 {len(files)}개: 한도 20,000의 80%를 넘으면 단지 JSON을 묶는 구조로 바꿔야 한다"
    assert sum(f.stat().st_size for f in files) < 512 * 2 ** 20 and max(f.stat().st_size for f in files) < 64 * 2 ** 20
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as t: t.add(root, arcname="assets")
    assert buf.tell() < 64 * 2 ** 20
