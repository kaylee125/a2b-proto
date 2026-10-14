"""과거 월별 실거래를 단지명 포함해 cache/data/sl_YYYYMM.json.gz 로 저장(이미 있는 월은 건너뜀, 월 단위 이어받기).
서울 25구 + 구리·하남·남양주(다산동만 쓰임). 일일 한도(429)면 30분 간격으로 재시도한다.
  python3 tools/fetch_history.py 201610 202309 [cache_dir]
수도권 확장 세트(수원 4구·성남 분당·안양 동안·화성 동탄구): python3 tools/fetch_history.py 201610 202609 cache metro  → sl_YYYYMMm.json.gz
  (화성은 2026-07 코드 개편으로 옛 41590이 전 기간 0건이라 새 코드 41597(동탄구)을 쓴다)
의왕시(내손동 등): python3 tools/fetch_history.py 201610 202609 cache uiwang  → sl_YYYYMMw.json.gz"""
import gzip, json, os, sys, time
from pathlib import Path
import molit
start, end = sys.argv[1], sys.argv[2]; S = Path(sys.argv[3]) if len(sys.argv) > 3 else Path(__file__).parent.parent / "cache"
SEOUL = [11110,11140,11170,11200,11215,11230,11260,11290,11305,11320,11350,11380,11410,11440,11470,11500,11530,11545,11560,11590,11620,11650,11680,11710,11740]
EXTRA = [41310, 41450, 41360]                                  # 구리·하남·남양주
METRO = [41111, 41113, 41115, 41117, 41135, 41173, 41597]      # 수원 장안·권선·팔달·영통, 성남 분당, 안양 동안, 화성 동탄구
SETS = {"metro": (METRO, "m"), "uiwang": ([41430], "w")}                    # 세트 이름 → (코드, 파일 접미사). uiwang = 의왕시(내손동 등)
SET = sys.argv[4] if len(sys.argv) > 4 else ""
key = molit.load_key()
URL = "https://apis.data.go.kr/1613000/RTMSDataSvcAptTrade/getRTMSDataSvcAptTrade"
def months(a, b):
    y, m = int(a[:4]), int(a[4:]); out = []
    while f"{y}{m:02d}" <= b: out.append(f"{y}{m:02d}"); y, m = (y, m + 1) if m < 12 else (y + 1, 1)
    return out
def fetch(ym, codes):
    rows = []
    for code in codes:
        page, got = 1, []
        while True:
            part, total = molit.parse_trades(molit.http_get(URL, {"serviceKey": key, "LAWD_CD": str(code), "DEAL_YMD": ym, "numOfRows": 1000, "pageNo": page})); got += part
            if not part or len(got) >= total: break
            page += 1
        rows += [dict(s=code, d=r["date"], a=r["amount"], ar=r["area"], c=int(r["canceled"]), t=r["dealing"][:1], u=r["umd"], n=r["apt"], b=r["build_year"], f=r["floor"]) for r in got]
    return rows
(S / "data").mkdir(parents=True, exist_ok=True); t0 = time.time()
for ym in months(start, end):
    path = S / "data" / f"sl_{ym}.json.gz"
    if SET in SETS: codes, suf = SETS[SET]; path = S / "data" / f"sl_{ym}{suf}.json.gz"
    elif ym == "202310": path = S / "data" / "sl_202310x.json.gz"; codes = EXTRA      # 2023-10 은 서울이 이미 있어 구리·하남·다산만 추가
    elif (S / "data" / f"sl_{ym}.json.gz").exists(): continue
    else: codes = SEOUL + EXTRA
    while not path.exists():
        try:
            rows = fetch(ym, codes); json.dump(rows, gzip.open(path, "wt", encoding="utf-8"), ensure_ascii=False); print(ym, len(rows), f"{time.time()-t0:.0f}s", "0건 코드:" + str(sorted(set(codes) - {r["s"] for r in rows})) if set(codes) - {r["s"] for r in rows} else "", flush=True)
        except Exception as e:
            print(ym, "대기(30분):", str(e)[:60], flush=True); time.sleep(1800)
print("완료", flush=True)
