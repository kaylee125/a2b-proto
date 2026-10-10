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
    assert len(RECS) == 6154 and sum(1 for r, _ in RECS if r["trend"]) == 3095
    E = [r for r, _ in RECS if r["trend"] and r["trend"]["m"] == "E"]
    assert len(E) == 2093 and sum(1 for r in E if r["trend"]["sure"]) == 1123
    assert {k: sum(1 for r in E if r["trend"]["s"] == k) for k in ("상승", "주춤", "하락")} == {"상승": 1776, "주춤": 214, "하락": 103}
    assert sum(1 for r, _ in RECS if r["trend"] and r["trend"]["m"] != "E") == 1002
    # 24개월 선형 모델(2,672개: 상승 2164·주춤 504·하락 4)은 그대로 재현되어야 함(서울·구리·하남·다산만일 때 1,958개: 상승 1646·주춤 310·하락 2)
    lin = {"상승": 0, "주춤": 0, "하락": 0}; n = 0
    for c in COMPS:
        d = bd.design(c["t"], END)
        if d: n += 1; lin[bd.status(*bd.six(d))[0]] += 1
    assert n == 2672 and lin == {"상승": 2164, "주춤": 504, "하락": 4}
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
    assert idx["meta"]["end"] == "2026-08-31" and len(idx["c"]) == 6154 and idx["meta"]["first_day"] < idx["meta"]["last_day"]
    assert all((p / "c" / f"{c['id']}.json").exists() for c in idx["c"][:50]) and len(list((p / "c").glob("*.json"))) == 6154
    assert "NaN" not in (p / "index.json").read_text(encoding="utf-8")


def test_reference_only_trends_are_never_certain_and_not_compared():
    ref = [r for r, _ in RECS if r["trend"] and r["trend"]["m"] != "E"]
    assert len(ref) == 1002 and sum(1 for r in ref if r["trend"]["w"] == 36) == 423
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
