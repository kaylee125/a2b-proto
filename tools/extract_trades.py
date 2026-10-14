"""세션에서 받아 둔 캐시(서울 25구 sl_*.json.gz, 수원·분당·동안·동탄 sl_*m.json.gz, 의왕 sl_*w.json.gz, 구리·하남 loop2_rows.json)와 dasan.db(다산동)에서
단지별 거래를 뽑아 data/complex_trades.json.gz 로 저장한다. 새 API 호출 없음.
  python3 tools/extract_trades.py [cache_dir=a2b-proto/cache] [dasan.db]"""
import glob, gzip, json, re, sqlite3, sys, collections, statistics as st
from datetime import date
from pathlib import Path
C = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent.parent / "cache"; DB = sys.argv[2] if len(sys.argv) > 2 else str(Path(__file__).parent.parent / "data" / "dasan.db")
import os
OUT = Path(os.environ.get("OUT") or Path(__file__).parent.parent / "data" / "complex_trades.json.gz")
D = date.fromisoformat; ROM = str.maketrans("ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ", "1234567890")
norm = lambda n: re.sub(r"[\s\-·.,()\[\]]", "", n.translate(ROM)).replace("아파트", "")
GU = {11110:"종로구",11140:"중구",11170:"용산구",11200:"성동구",11215:"광진구",11230:"동대문구",11260:"중랑구",11290:"성북구",11305:"강북구",11320:"도봉구",11350:"노원구",11380:"은평구",11410:"서대문구",11440:"마포구",11470:"양천구",11500:"강서구",
      11530:"구로구",11545:"금천구",11560:"영등포구",11590:"동작구",11620:"관악구",11650:"서초구",11680:"강남구",11710:"송파구",11740:"강동구",41310:"구리시",41450:"하남시",41360:"남양주시",
      41111:"수원시 장안구",41113:"수원시 권선구",41115:"수원시 팔달구",41117:"수원시 영통구",41135:"성남시 분당구",41173:"안양시 동안구",41597:"화성시 동탄구",41430:"의왕시"}
REG = {s: ("서울" if s < 20000 else "경기") for s in GU}
rows = []                                                    # (sgg, umd, name, area, date, amount, build, floor)
for p in sorted(glob.glob(str(C / "data" / "sl_*.json.gz"))):
    for r in json.load(gzip.open(p, "rt", encoding="utf-8")):
        if r["s"] == 41360 and r["u"] != "다산동": continue                        # fetch_history 가 남양주 전체를 받으므로 다산동만
        if not r["c"] and r["t"] != "직": rows.append((r["s"], r["u"], r["n"], r["ar"], D(r["d"]), r["a"], r["b"], r["f"]))
for r in json.load(open(C / "data" / "loop2_rows.json")):
    if r["region"] in ("구리", "하남") and not r["canceled"] and r["dealing"] != "직거래": rows.append((r["sgg"], r["umd"], r["apt"], r["area"], D(r["date"]), r["amount"], r["by"], r["floor"]))
if not Path(DB).exists(): print(f"참고: {DB} 없음 → 다산동 일일 수집분은 건너뜁니다", file=sys.stderr)
for apt, area, d, amt, by, dl, cn, fl in (sqlite3.connect(DB).execute("select apt, area, date, amount, build_year, dealing, canceled, floor from trade") if Path(DB).exists() else []):
    if not cn and dl != "직거래": rows.append((41360, "다산동", apt, area, D(d), amt, by, fl))
ids = collections.defaultdict(list)
for t in rows: ids[(t[0], t[1], norm(t[2]))].append(t)
out = []
for (s, u, nm), ts in sorted(ids.items()):
    ys = sorted({t[6] for t in ts if t[6]}); cut = [ys[0]] if ys else [0]
    for y in ys[1:]:
        if y - cut[-1] >= 3: cut.append(y)                   # 같은 동·이름에서 준공연도 차 ≥3년이면 별도 단지
    for c0 in cut:
        grp = [t for t in ts if (not t[6]) or (max([c for c in cut if c <= t[6]] or [cut[0]]) == c0)]
        if len(grp) < 12: continue
        grp.sort(key=lambda x: x[4]); name = collections.Counter(x[2] for x in grp).most_common(1)[0][0]
        out.append(dict(sgg=s, gu=GU[s], reg=REG[s], umd=u, name=name, by=c0 or None, t=[[x[4].toordinal(), x[5], round(x[3], 2), x[7]] for x in grp]))
OUT.parent.mkdir(exist_ok=True)
json.dump(out, gzip.open(OUT, "wt", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print(f"단지 {len(out):,}개, 거래 {sum(len(c['t']) for c in out):,}건 → {OUT} ({OUT.stat().st_size/1e6:.1f}MB)")
