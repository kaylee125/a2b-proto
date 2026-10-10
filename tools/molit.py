"""국토부 실거래 API 호출 도구 (fetch_history.py 용). 키는 환경변수 DATA_GO_KR_SERVICE_KEY 또는 프로젝트 루트의 .env."""
import os, time, urllib.error, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_key(path=ROOT / ".env"):
    if os.environ.get("DATA_GO_KR_SERVICE_KEY"):
        return os.environ["DATA_GO_KR_SERVICE_KEY"]
    for line in Path(path).read_text().splitlines() if Path(path).exists() else []:
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.split("=", 1)
            if k.strip() == "DATA_GO_KR_SERVICE_KEY":
                return v.strip().strip('"').strip("'")
    raise SystemExit("DATA_GO_KR_SERVICE_KEY 가 없습니다. .env.example 을 .env 로 복사해 채우거나 환경변수로 지정하세요.")


def http_get(url, params, tries=5, timeout=30):
    """네트워크 오류·5xx·429만 2·4·8·16초 간격으로 재시도한다. 키 오류(403)·없는 주소(404) 같은 4xx는 바로 실패."""
    full = url + "?" + urllib.parse.urlencode(params)
    for i in range(tries):
        try:
            req = urllib.request.Request(full, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as e:
            permanent = isinstance(e, urllib.error.HTTPError) and e.code < 500 and e.code != 429
            if permanent or i == tries - 1:
                raise
            time.sleep(2 ** (i + 1))


def parse_trades(xml):
    root = ET.fromstring(xml)
    code = root.findtext("header/resultCode")
    if code not in ("000", "00"):
        raise RuntimeError(f"trade api {code}: {root.findtext('header/resultMsg')}")
    rows = []
    for it in root.iter("item"):
        g = lambda k: (it.findtext(k) or "").strip()
        rows.append(dict(
            apt=g("aptNm"), dong=g("aptDong"), floor=int(g("floor") or 0), area=float(g("excluUseAr")),
            date=f"{g('dealYear')}-{int(g('dealMonth')):02d}-{int(g('dealDay')):02d}",
            amount=int(g("dealAmount").replace(",", "")), build_year=int(g("buildYear") or 0),
            dealing=g("dealingGbn"), canceled=bool(g("cdealType")), cancel_date=g("cdealDay"),
            rgst=g("rgstDate"), jibun=g("jibun"), umd=g("umdNm")))
    return rows, int(root.findtext("body/totalCount") or 0)
