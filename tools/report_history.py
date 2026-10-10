"""10년 분석 리포트(앱 반영과 별개): 구별 지수·하락기 낙폭, 강남권→주변 선후행(순환 이동 귀무분포), 월별 거래 건수 점검.
  python3 tools/report_history.py"""
import glob, gzip, json, math, statistics as st, sys
from pathlib import Path
ROOT = Path(__file__).parent.parent; sys.path.insert(0, str(ROOT))
H = json.load(open(ROOT / "site" / "data" / "hist.json", encoding="utf-8")); n = H["n"]
by = {}
for v in H["c"].values(): by.setdefault(v["gu"], []).append(v["p"])
def gu_changes(ps):                                                  # 분기별 로그 변화 중위값(양 분기 모두 있는 단지만, 5개 이상일 때)
    out = []
    for q in range(1, n):
        x = [math.log(p[q] / p[q - 1]) for p in ps if p[q] is not None and p[q - 1] is not None]; out.append(st.median(x) if len(x) >= 5 else None)
    return out
G = {g: gu_changes(ps) for g, ps in by.items() if g.endswith("구") and len(ps) >= 10 and g not in ("구리시",)}
SEOUL = [g for g in G if g not in ("하남시", "남양주시")]
print(f"구 지수 산출 {len(SEOUL)}개 구")
print("\n[구별 하락기 방어력] (단지 중위 낙폭, 단지 수)")
rows = sorted(((H["gu"][g]["med"], g, H["gu"][g]["n"]) for g in H["gu"]), key=lambda x: x[0])
for m, g, k in rows: print(f"  {g:6s} {m:+.1%}  ({k}개)")
core = ["강남구", "서초구", "송파구"]; rest = [g for g in SEOUL if g not in core]
def avg(gs, i):
    v = [G[g][i] for g in gs if G[g][i] is not None]; return sum(v) / len(v) if len(v) == len(gs) else None
x = [avg(core, i) for i in range(n - 1)]; y = [avg(rest, i) for i in range(n - 1)]
def corr(a, b):
    p = [(u, v) for u, v in zip(a, b) if u is not None and v is not None]
    if len(p) < 12: return None
    mu, mv = st.mean(u for u, _ in p), st.mean(v for _, v in p); num = sum((u - mu) * (v - mv) for u, v in p)
    d = math.sqrt(sum((u - mu) ** 2 for u, _ in p) * sum((v - mv) ** 2 for _, v in p)); return num / d if d else None
def at(k, a, b): return corr(a[:len(a) - k] if k else a, b[k:])      # a(t) vs b(t+k)
print("\n[선후행] 강남·서초·송파(A) vs 나머지 서울 구(B) 분기 변화율 상관 — 귀무: A를 순환 이동")
for k in range(-3, 5):
    r = at(k, x, y) if k >= 0 else at(-k, y, x)
    null = [c for s in range(4, len(x) - 3) for c in [at(max(k, 0) if k >= 0 else 0, x[s:] + x[:s], y) if k >= 0 else at(-k, y, x[s:] + x[:s])] if c is not None]
    p = sum(1 for c in null if abs(c) >= abs(r)) / len(null) if null and r is not None else None
    lab = "A가 B를 k분기 앞섬" if k > 0 else "동시" if k == 0 else "B가 A를 앞섬"
    print(f"  k={k:+d} ({lab:16s}) r={r:+.2f}  p≈{p:.2f}" if r is not None else f"  k={k:+d} 표본 부족")
print("  (분기 38개 안팎의 짧은 표본이라 p<0.05라도 우연일 가능성이 크고, 다중 비교(8개 k) 보정 전 수치)")
print("\n[월별 서울 거래 건수 점검] 2019~2021 (취소 제외 전, 서울 25구)")
cnt = {}
for f in sorted(glob.glob(str(ROOT / "cache" / "data" / "sl_20*.json.gz"))):
    ym = Path(f).name[3:9]
    if "2019" <= ym[:4] <= "2021": cnt[ym] = sum(1 for r in json.load(gzip.open(f, "rt", encoding="utf-8")) if r["s"] < 20000)
print("  " + "  ".join(f"{k[2:]}:{v}" for k, v in cnt.items()))
