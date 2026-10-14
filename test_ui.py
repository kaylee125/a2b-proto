"""앱 UI 종단 검증: 로컬 서버 + 헤드리스 Chrome으로 화면을 실제로 그린 뒤 #view만 검사하고,
화면의 숫자를 JS와 무관한 Python 계산(index.json·상세 json·자금 계획 공식)과 대조한다."""
import functools, http.server, json, math, re, subprocess, threading
from pathlib import Path

import pytest

CHROME = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
SITE = Path(__file__).parent / "site"
pytestmark = pytest.mark.skipif(not CHROME.exists(), reason="Chrome 없음")
IDX = json.loads((SITE / "data" / "index.json").read_text(encoding="utf-8"))
C = IDX["c"]
MINE = next(c for c in C if c["sgg"] == 41360 and "한양수자인리버파크" in c["name"])
qn = lambda i: (lambda t: f"{t // 4}Q{t % 4 + 1}")(2016 * 4 + 3 + i)


def _examples():                                                           # app.js exampleBs 와 같은 규칙을 독립적으로 구현
    ok = [c for c in C if c["trend"] and c["trend"]["w"] == 24 and c.get("px") and 74 <= c["pa"] <= 115 and c["n12"] >= 30 and c["id"] != MINE["id"] and MINE["px"] * 1.15 <= c["px"] <= MINE["px"] * 1.6]
    out = []
    for c in sorted(ok, key=lambda c: -c["n12"]):
        if len(out) < 2 and all(o["gu"] != c["gu"] for o in out): out.append(c)
    return out


BEXAMPLES = [next(c for c in C if c["gu"] == gu and c["name"] == nm) for gu, nm in (("관악구", "벽산블루밍"), ("노원구", "한진한화그랑빌"))]   # 고정 예시(app.js EXAMPLES)
assert [b["id"] for b in BEXAMPLES] == ["f8834abe", "5c7b8df1"] and all(b["pa"] == 85 for b in BEXAMPLES)
FB = next(c for c in C if c["trend"] and c["trend"]["w"] == 36)
REF24 = next(c for c in C if c["trend"] and c["trend"]["w"] == 24 and c["trend"]["m"] == "A")
RULES = json.loads((SITE / "data" / "rules.json").read_text(encoding="utf-8"))
CAND = json.loads((SITE / "data" / "cand.json").read_text(encoding="utf-8"))
HIST = json.loads((SITE / "data" / "hist.json").read_text(encoding="utf-8"))
NOTREND = next(c for c in C if not c["trend"] and c["n12"] >= 15)
det = lambda c: json.loads((SITE / "data" / "c" / f"{c['id']}.json").read_text(encoding="utf-8"))


HARNESS = """<!doctype html><meta charset=utf-8><iframe id=f style="width:430px;height:900px" src="/?nosplash&theme=light&nomotion#/home"></iframe><pre id=out></pre><script>
const wait = ms => new Promise(r => setTimeout(r, ms)); const f = document.getElementById('f');
if (location.search.startsWith('?stale=')) { f.src = '/?nosplash&theme=light&nomotion#/home'; try { localStorage.setItem('a2b.v1', JSON.stringify({ a: null, bs: [{ id: location.search.slice(7), type: null, tier: 1, sample: true }], plan: {}, theme: 'auto', intro: 1 })); } catch (e) {} }
if (location.search.startsWith('?fp=')) { f.src = '/?nosplash&theme=light&nomotion#/' + decodeURIComponent(location.search.slice(4)); }
if (location.search === '?loc=1') f.src = '/?nosplash&theme=light&nomotion#/find';
if (location.search === '?area=1') f.src = '/?nosplash&theme=light&nomotion#/area';
if (location.search === '?unit=1') f.src = '/?nosplash&theme=light&nomotion#/home';
if (location.search === '?asearch=1') f.src = '/?nosplash&theme=light&nomotion#/area';
if (location.search.startsWith('?dv=1')) f.src = '/?nosplash&theme=light&nomotion#/home';
if (location.search === '?tourflow=1') f.src = '/?nosplash&theme=light&nomotion&tour=1#/home';
if (location.search === '?tourauto=1') f.src = '/?theme=light&nomotion#/home';
if (location.search === '?edit=1') f.src = '/?nosplash&theme=light&nomotion#/home';
if (location.search === '?fab=1') f.src = '/?nosplash&theme=light&nomotion#/home';
if (location.search.startsWith('?tip=')) { const q = new URLSearchParams(location.search); f.src = '/?nosplash&theme=light&nomotion#/c/' + q.get('id'); }
f.onload = async () => { const d = f.contentDocument, w = f.contentWindow, log = [];
  if (location.search.startsWith('?tip=')) { try { await wait(900); const m = +new URLSearchParams(location.search).get('tip'), sv = d.querySelector('#chart'), r = sv.getBoundingClientRect(), X = 40 + 310 * (m + 24) / 24;
      sv.dispatchEvent(new w.PointerEvent('pointermove', { bubbles: true, clientX: r.left + X * r.width / 360, clientY: r.top + 40 })); await wait(100); const tp = d.querySelector('#tip'); log.push('툴팁=' + tp.textContent.replace(/\\s+/g, ' ') + ' 불투명=' + tp.style.opacity); } catch (e) { log.push('ERR ' + e.message); }
    document.getElementById('out').textContent = log.join('\\n'); return; }
  if (location.search.startsWith('?stale=')) { await wait(800); log.push(d.querySelector('#view').textContent.replace(/\\s+/g, ' ')); document.getElementById('out').textContent = log.join('\\n'); return; }
  if (location.search.startsWith('?fp=')) { try { const until = async s => { for (let k = 0; k < 60 && !d.querySelector(s); k++) await wait(250); }; await until('[data-act^=fplan]'); const route = decodeURIComponent(location.search.slice(4)), n = Math.min(5, d.querySelectorAll('[data-act^=fplan]').length);
      for (let i = 0; i < n; i++) { f.contentWindow.location.hash = '#/' + route + '&x=' + i; await wait(300); await until('#view .card.tap [data-act^=fplan]'); const cards = [...d.querySelectorAll('#view .card.tap')].filter(c => c.querySelector('[data-act^=fplan]')), c = cards[i]; if (!c) break; const lab = c.querySelector('.badge').textContent.trim(), nm = c.querySelector('.rc-name').textContent; c.querySelector('[data-act^=fplan]').click(); await until('#res .res-big'); await wait(200);
        log.push('카드' + i + '|' + lab + ' ' + nm + '|' + (d.querySelector('#res .res-big') || {textContent: 'none'}).textContent.trim()); } } catch (e) { log.push('ERR ' + e.message); }
    document.getElementById('out').textContent = log.join('\\n'); return; }
  if (location.search.startsWith('?dv=1')) { try { await wait(1500); f.contentWindow.location.hash = '#/find?loc=11350'; await wait(1500); f.contentWindow.location.hash = '#/area'; await wait(1200); f.contentWindow.location.hash = '#/c/' + new URLSearchParams(location.search).get('id'); await wait(1200);
      log.push('데이터요청=' + JSON.stringify(w.performance.getEntriesByType('resource').map(e => e.name).filter(u => /\\/data\\//.test(u)).map(u => u.replace(/^.*\\/data\\//, 'data/'))));
    } catch (e) { log.push('ERR ' + e.message); }
    document.getElementById('out').textContent = log.join('\\n'); return; }
  if (location.search === '?tourflow=1') { try { const click = s => { const e = d.querySelector(s); if (!e) throw new Error('없음 ' + s); e.click(); }, tx = s => d.querySelector(s).textContent.replace(/\\s+/g, ' '), on = () => d.querySelector('#sheet').classList.contains('on'), ls = () => JSON.parse(w.localStorage.getItem('a2b.v1') || '{}');
      await wait(1200); for (let i = 0; i < 5; i++) { log.push('단계' + i + '=' + tx('#sh-h') + '|' + tx('#sh-b .tour-h') + '|' + tx('#sh-b .tour-next')); if (i < 4) { click('#sh-b .tour-next'); await wait(200); } }
      click('#sh-b .tour-next'); await wait(300); log.push('끝=' + on());
      click('[data-go="#/settings"]'); await wait(500); click('[data-act="tour:0"]'); await wait(300); log.push('다시=' + tx('#sh-h') + '|' + on());
      d.dispatchEvent(new w.KeyboardEvent('keydown', { key: 'Escape', bubbles: true })); await wait(300); log.push('Esc=' + on());
      click('[data-act="tour:0"]'); await wait(200); for (let i = 0; i < 3; i++) { click('#sh-b .tour-next'); await wait(150); } click('#sh-b [data-go="#/find"]'); await wait(700); log.push('링크=' + w.location.hash + '|' + on());
      click('#sh-b .tour-skip') ;
    } catch (e) { log.push('ERR ' + e.message); }
    document.getElementById('out').textContent = log.join('\\n'); return; }
  if (location.search === '?tourauto=1') { try { const on = () => d.querySelector('#sheet').classList.contains('on'), ls = () => JSON.parse(w.localStorage.getItem('a2b.v1') || '{}'), tx = s => d.querySelector(s).textContent.replace(/\\s+/g, ' ');
      await wait(4500); log.push('첫방문=' + on() + '|' + tx('#sh-h') + '|' + ls().tour);
      d.querySelector('#bd').click(); await wait(300); log.push('닫힘=' + on()); f.onload = null; f.contentWindow.location.reload(); await wait(1500);
      const d2 = f.contentDocument; await wait(4000); log.push('재방문=' + d2.querySelector('#sheet').classList.contains('on'));
    } catch (e) { log.push('ERR ' + e.message); }
    document.getElementById('out').textContent = log.join('\\n'); return; }
  if (location.search === '?asearch=1') { try { const click = s => { const e = d.querySelector(s); if (!e) throw new Error('없음 ' + s); e.click(); }, ls = () => JSON.parse(w.localStorage.getItem('a2b.v1') || '{}'), tx = s => d.querySelector(s).textContent.replace(/\\s+/g, ' '), until = async s => { for (let k = 0; k < 40 && !d.querySelector(s); k++) await wait(250); };
      const type = async v => { const i = d.querySelector('#aq'); i.value = v; i.dispatchEvent(new w.Event('input', { bubbles: true })); await wait(150); };
      await until('[data-act=aloc]'); click('[data-act=aloc]'); await wait(200); await type('정자'); log.push('정자=' + tx('#al'));
      click('[data-act="atd:41135:정자동"]'); await wait(200); log.push('선택후=' + tx('#al').slice(0, 90) + '|' + JSON.stringify(ls().areas) + '|' + (d.querySelector('#aq') ? d.querySelector('#aq').value : '입력칸 사라짐'));
      await type('성남 정자'); log.push('성남정자=' + tx('#al')); await type('분당'); log.push('분당=' + tx('#al').slice(0, 130)); await type('zzzz'); log.push('없음=' + tx('#al')); await type(''); log.push('비움=' + tx('#al').slice(0, 80));
      click('[data-act=adone]'); await wait(800); log.push('뷰=' + tx('#view').slice(0, 400));
    } catch (e) { log.push('ERR ' + e.message); }
    document.getElementById('out').textContent = log.join('\\n'); return; }
  if (location.search === '?unit=1') { try { const click = s => { const e = d.querySelector(s); if (!e) throw new Error('없음 ' + s); e.click(); }, ls = () => JSON.parse(w.localStorage.getItem('a2b.v1') || '{}'), tx = s => d.querySelector(s).textContent.replace(/\\s+/g, ' ');
      await wait(1000); log.push('전=' + tx('#bar') + '|' + ls().unit); click('[data-act="unit:py"]'); await wait(700); log.push('후=' + tx('#bar') + '|' + ls().unit + '|' + tx('#view').slice(0, 300));
      click('[data-go="#/settings"]'); await wait(500); log.push('설정=' + tx('#view').slice(0, 120)); click('#view [data-act="unit:m2"]'); await wait(400); click('[data-go="#/home"]'); await wait(800); log.push('복귀=' + tx('#bar') + '|' + ls().unit);
    } catch (e) { log.push('ERR ' + e.message); }
    document.getElementById('out').textContent = log.join('\\n'); return; }
  if (location.search === '?area=1') { try { const click = s => { const e = d.querySelector(s); if (!e) throw new Error('없음 ' + s); e.click(); }, ls = () => JSON.parse(w.localStorage.getItem('a2b.v1') || '{}'), until = async s => { for (let k = 0; k < 40 && !d.querySelector(s); k++) await wait(250); };
      await until('[data-act=aloc]'); log.push('처음=' + JSON.stringify(ls().areas)); click('[data-act=aloc]'); await wait(200); click('[data-act="adong:11350"]'); await wait(200); click('[data-act="atd:11350:월계동"]'); await wait(200);
      log.push('동시트=' + d.querySelector('#sh-b').textContent.replace(/\\s+/g, ' ').slice(0, 60)); click('[data-act=aloc]'); await wait(200); click('[data-act="at:11680"]'); await wait(200); click('[data-act=adone]'); await wait(800);
      log.push('선택=' + JSON.stringify(ls().areas)); log.push('뷰=' + d.querySelector('#view').textContent.replace(/\\s+/g, ' ').slice(0, 500)); click('#view [data-act="atd:41360:다산동"]'); await wait(600); log.push('빼기후=' + JSON.stringify(ls().areas));
      click('#view [data-act="atd:11350:월계동"]'); await wait(300); click('#view [data-act="at:11680"]'); await wait(500); log.push('비움=' + JSON.stringify(ls().areas) + ' ' + d.querySelector('#view').textContent.replace(/\\s+/g, ' ').slice(0, 70));
    } catch (e) { log.push('ERR ' + e.message); }
    document.getElementById('out').textContent = log.join('\\n'); return; }
  if (location.search === '?loc=1') { try { await wait(1000); const click = s => d.querySelector(s).click(); click('[data-act=floc]'); await wait(300); log.push('시트=' + d.querySelector('#sh-b').textContent.replace(/\\s+/g, ' ')); click('[data-act="loc:11350"]'); await wait(200); log.push('구선택=' + w.localStorage.getItem('a2b.v1').slice(0, 400)); click('[data-act="dong:11350"]'); await wait(300); click('[data-act^="dloc:11350:"]'); await wait(200); log.push('동선택=' + JSON.stringify(JSON.parse(w.localStorage.getItem('a2b.v1')).find)); click('[data-act=floc]'); await wait(200); click('[data-act=fdone]'); await wait(900); log.push('요약=' + d.querySelector('#locsum').textContent); } catch (e) { log.push('ERR ' + e.message); }
    document.getElementById('out').textContent = log.join('\\n'); return; }
  if (location.search === '?fab=1') { try { await wait(800); d.querySelector('#fab').click(); await wait(300); log.push('시트=' + d.querySelector('#sh-b').textContent.replace(/\\s+/g, ' ')); d.querySelector('#sh-b [data-go="#/find"]').click(); await wait(900); log.push('찾기화면=' + d.querySelector('#bar .t').textContent); } catch (e) { log.push('ERR ' + e.message); }
    document.getElementById('out').textContent = log.join('\\n'); return; }
  if (location.search === '?edit=1') { try { const click = s => d.querySelector(s).click(), until = async s => { for (let k = 0; k < 40 && !d.querySelector(s); k++) await wait(250); }, ls = () => JSON.parse(w.localStorage.getItem('a2b.v1'));
      await until('[data-act=own]'); click('[data-act=own]'); await wait(200); d.querySelector('#ob').value = '95000'; d.querySelector('#oy').value = '2025-08'; click('[data-act=own-save]'); await wait(700);
      const bs0 = ls().bs.map(b => ({ ...b })); log.push('B전=' + JSON.stringify(bs0));
      click('[data-act=kebab-a]'); await wait(200); log.push('A메뉴=' + d.querySelector('#sh-b').textContent.replace(/\\s+/g, ' ')); click('[data-act^="edit:a:"]'); await until('#fl'); log.push('A칩=' + [...d.querySelectorAll('#ty button')].map(b => b.dataset.ty + (b.classList.contains('on') ? '*' : '')).join(',') + ' 층=' + d.querySelector('#fl').value);
      click('#ty [data-ty="112"]'); d.querySelector('#fl').value = '3'; click('[data-act=commit]'); await wait(800); log.push('A바=' + d.querySelector('#bar .ad').textContent); log.push('A저장=' + JSON.stringify(ls().a));
      click('#view [data-act^="kebab:"]'); await wait(200); log.push('B메뉴=' + d.querySelector('#sh-b').textContent.replace(/\\s+/g, ' ')); click('[data-act^="edit:b:"]'); await until('#tr'); const chips = [...d.querySelectorAll('#ty button')]; log.push('B칩=' + chips.map(b => b.dataset.ty + (b.classList.contains('on') ? '*' : '')).join(','));
      const other = chips.find(b => !b.classList.contains('on')); other.click(); click('#tr [data-tr="2"]'); click('[data-act=commit]'); await wait(800); log.push('B후=' + JSON.stringify(ls().bs));
      const id2 = ls().bs[1].id; f.contentWindow.location.hash = '#/c/' + id2; await until('.chips button[data-go*="?t="]'); const alt = [...d.querySelectorAll('.chips button[data-go*="?t="]')].find(b => !b.classList.contains('on')); log.push('상세저장상태=' + (d.querySelector('[data-act^=savetype]') ? '버튼있음' : d.querySelector('#view').textContent.includes('후보로 저장된 평형이에요') ? '저장됨' : '없음'));
      alt.click(); await until('[data-act^=savetype]'); const want = +d.querySelector('[data-act^=savetype]').dataset.act.split(':')[2]; click('[data-act^=savetype]'); await wait(700); log.push('상세저장=' + want + ' ' + JSON.stringify(ls().bs[1])); log.push('저장후=' + (d.querySelector('#view').textContent.includes('후보로 저장된 평형이에요') ? '표시' : '없음'));
    } catch (e) { log.push('ERR ' + e.message); }
    document.getElementById('out').textContent = log.join('\\n'); return; }
  if (location.search === '?own') { try { await wait(600); const click = s => d.querySelector(s).click(); click('[data-act=own]'); await wait(200); d.querySelector('#ob').value = '95000'; d.querySelector('#oy').value = '2025-08'; click('[data-act=own-save]'); await wait(600);
      log.push('카드=' + d.querySelector('#view .card .rel.tap').textContent.replace(/\\s+/g, ' ')); click('[data-act=own]'); await wait(200); click('[data-act=own-clear]'); await wait(500); log.push('지운후=' + d.querySelector('#view .card .rel.tap').textContent.replace(/\\s+/g, ' ')); } catch (e) { log.push('ERR ' + e.message); }
    document.getElementById('out').textContent = log.join('\\n'); return; }
  const click = s => { const e = d.querySelector(s); if (!e) throw new Error('없음 ' + s); e.click(); };
  try { await wait(600);
    click('[data-act=pick-a]'); await wait(200); const q = d.querySelector('#q'); q.value = '래미안 퍼스티지'; q.dispatchEvent(new Event('input', {bubbles: true})); await wait(100);
    log.push('A후보=' + d.querySelector('.pick b').textContent); click('.pick'); await wait(500);
    log.push('A칩=' + d.querySelectorAll('#ty button').length); d.querySelector('#fl').value = '15'; click('[data-act=commit]'); await wait(700);
    log.push('A뷰=' + d.querySelector('#view').textContent.replace(/\\s+/g, ' ').slice(0, 160)); log.push('바=' + d.querySelector('#bar').textContent.replace(/\\s+/g, ' '));
    click('#fab'); await wait(200); click('[data-act=pick-b]'); await wait(200); const q2 = d.querySelector('#q'); q2.value = '헬리오시티'; q2.dispatchEvent(new Event('input', {bubbles: true})); await wait(100);
    click('.pick'); await wait(500); click('#tr [data-tr="2"]'); click('[data-act=commit]'); await wait(700);
    log.push('B카드=' + d.querySelectorAll('#view [data-act^="kebab:"]').length + ' 예시=' + (d.querySelector('#view').textContent.includes('후보 B · 예시') ? 'Y' : 'N'));
    click('[data-act^="kebab:"]'); await wait(200); log.push('케밥=' + d.querySelector('#sh-b').textContent.replace(/\\s+/g, ' ')); click('[data-act^=del]'); await wait(500);
    log.push('삭제후B=' + d.querySelectorAll('#view [data-act^="kebab:"]').length + ' ls=' + (w.localStorage.getItem('a2b.v1') || '').slice(0, 90));
    click('[data-go="#/settings"]'); await wait(300); click('[data-act=reset]'); await wait(700); log.push('초기화후=' + d.querySelector('#bar').textContent.replace(/\\s+/g, ' '));
  } catch (e) { log.push('ERR ' + e.message); }
  document.getElementById('out').textContent = log.join('\\n'); document.title = 'done'; };
</script>"""


@pytest.fixture(scope="module")
def base():
    class H(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a, **k): pass
        def do_GET(self):                                                       # 조작 시나리오용 하니스(같은 출처 iframe)
            if self.path.startswith("/__t.html"):
                body = HARNESS.encode(); self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
            else: super().do_GET()
    h = functools.partial(H, directory=str(SITE))
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), h); threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"; srv.shutdown()


def chrome(args, tries=3):
    """헤드리스 Chrome이 드물게 시작 단계에서 멈추므로(앱 문제 아님: 같은 화면이 1초 내 반복 성공) 시간 초과 시 재시도."""
    for i in range(tries):
        try: return subprocess.run([str(CHROME), "--headless=new", "--disable-gpu", *args], capture_output=True, text=True, timeout=40).stdout
        except subprocess.TimeoutExpired:
            if i == tries - 1: raise


def dom(base, route, extra="nosplash&theme=light&nomotion"):
    return chrome(["--virtual-time-budget=6000", "--dump-dom", f"{base}/?{extra}#/{route}"])


def view(html):
    m = re.search(r'<main id="view"[^>]*>(.*?)</main>', html, re.S); assert m, "main#view 없음"; return m.group(1)


def text(v): return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", v))


def won(v):
    s, a = ("-" if v < 0 else ""), abs(int(math.floor(v + .5))); e, m = divmod(a, 10000)
    return s + (f"{e}억" + (f" {m:,}만" if m else "") if e else f"{m:,}만")


def pct(r, d=1): return f"{'+' if r >= 0 else '-'}{abs(r * 100):.{d}f}%"


ROUTES = ["home", f"c/{MINE['id']}", f"c/{MINE['id']}?t=112&range=1y", f"c/{NOTREND['id']}", f"c/{FB['id']}", f"cmp?b={BEXAMPLES[0]['id']}", f"cmp?b={BEXAMPLES[1]['id']}", f"c/{BEXAMPLES[0]['id']}?range=1y", "plan", "area", "area?loc=11350", "area?loc=41360:다산동,11350:월계동,11680", f"plan?b={BEXAMPLES[1]['id']}", "settings", "find", "find?loc=11350&income=12000&cash=10000", "find?loc=11350,41360&mode=gap&income=12000&cash=10000&tohu=1", "find?loc=11350:월계동&cash=0&aloan=60000&cls=가능,빠듯,불가"]


@pytest.mark.parametrize("route", ROUTES)
def test_route_renders_cleanly(base, route):
    html = dom(base, route)
    assert '<pre id="err">' not in html, re.findall(r'<pre id="err">([^<]*)', html)
    v = view(html); assert len(v) > 600, "화면이 비어 있음"
    assert "불러오지 못했습니다" not in v and "오류가 났습니다" not in v and "찾을 수 없습니다" not in v
    assert not re.search(r"NaN|undefined|\[object|Infinity", v)
    assert not re.search(r"전망|예상|추천|오를|내릴|할 것|지정되면|정책 레이더", v)


def test_home_cards_match_data(base):
    t = text(view(dom(base, "home"))); m = MINE["trend"]
    assert f"{pct(m['r'])} 최근 6개월" in t and f"{pct(m['lo'])} ~ {pct(m['hi'])}" in t and m["s"] in t
    d = MINE["dong"]; assert f"{MINE['umd']} {d['n']}개 단지" in t and f"{d['n']}개 중 {d['rank']}위" in t and f"중간값 {pct(d['med'])}" in t
    diff = (m['r'] - d['med']) * 100; assert f"중간값보다 {abs(diff):.1f}%p {'높아요' if diff >= 0 else '낮아요'}" in t
    e = det(MINE)["est"]["98|2"]; assert won(e[0]) in t and f"{won(e[1])} ~ {won(e[2])}" in t           # 98㎡ 9층 = 고층
    for b in BEXAMPLES: assert b["name"] in t and pct(b["trend"]["r"]) in t and b["px"] > MINE["px"] * 1.15       # 예시 후보는 A보다 15% 이상 비싼 상급지 이동
    assert t.count("후보 B · 예시") == 2 and "예시 단지로 채워져 있어요" in t


def test_detail_numbers_and_floor_tiers(base):
    d = det(MINE); t = text(view(dom(base, f"c/{MINE['id']}")))
    for tier in range(3): e = d["est"][f"98|{tier}"]; assert f"{won(e[0])} ({won(e[1])} ~ {won(e[2])})" in t
    assert f"({d['tiers'][0] - 1}층 이하)" in t and f"({d['tiers'][1]}층 이상)" in t
    assert f"최근 12개월 신고 거래 {MINE['n12']}건" in t and "98㎡ · 28건" in t and "112㎡ · 4건" in t
    assert len(re.findall(r"\d{4}-\d\d-\d\d", t)) >= 12                                                # 최근 거래 12건


def test_chart_has_dots_and_band(base):
    v = view(dom(base, f"c/{MINE['id']}"))
    chart = re.search(r'<svg class="chart" id="chart".*?</svg>', v, re.S).group(0)                              # 24개월 차트만(10년 차트와 구분)
    assert chart.count("<circle") == sum(1 for x in det(MINE)["scatter"] if x[2] == 98) and "<path" in chart


def test_untrended_complex_says_so(base):
    t = text(view(dom(base, f"c/{NOTREND['id']}"))); assert "표본 부족" in t and "20건에 못 미쳐" in t and "차트" not in t.replace("차트를 그리지 않았어요", "")


def acq(buy, area):
    base_ = 1 if buy <= 60000 else (buy / 1e4 * 2 / 3 - 3 if buy <= 90000 else 3)
    return (base_ + base_ * .1 + (.2 if area > 85 else 0)) / 100


def bro(v):
    """서울시 조례 요율표(land.seoul.go.kr, 2026-10 확인): 상한요율과 한도액(5천만 미만 25만원, 5천만~2억 80만원)."""
    r = next(r for lim, r in [(5000, .006), (20000, .005), (90000, .004), (120000, .005), (150000, .006), (1e18, .007)] if v < lim); f = v * r
    return min(f, 25) if v < 5000 else min(f, 80) if v < 20000 else f


def gap(sale, buy, aloan, bloan, cash, move, tax, area):
    r = lambda x: math.floor(x + .5)
    pro = sale - aloan - r(bro(sale)) - tax
    need = buy + r(buy * acq(buy, area)) + r(bro(buy)) + r(buy * .003) + move - bloan
    return need - pro - cash


@pytest.mark.parametrize("sale,buy,aloan,bloan,cash,move,tax", [(120000, 80000, 30000, 20000, 15000, 300, 0), (95000, 130000, 0, 40000, 20000, 500, 1200), (105000, 55000, 10000, 0, 0, 300, 0), (19000, 19000, 0, 0, 5000, 300, 0)])
def test_plan_matches_independent_formula(base, sale, buy, aloan, bloan, cash, move, tax):
    b = BEXAMPLES[0]; area = next(t["m"] for t in det(b)["types"] if t["a"] == b["pa"])
    q = f"plan?b={b['id']}&sale={sale}&buy={buy}&aloan={aloan}&bloan={bloan}&cash={cash}&move={move}&tax={tax}"
    t = text(view(dom(base, q))); g = gap(sale, buy, aloan, bloan, cash, move, tax, area)
    want = f"{won(g)} 부족" if g > 0 else f"{won(-g)} 여유"
    assert want in t, (want, t[t.find("기준 시나리오"):][:120])


def test_plan_sensitivity_grid_values(base):
    b = BEXAMPLES[0]; d = det(b); area = next(t["m"] for t in d["types"] if t["a"] == b["pa"]); args = (30000, 20000, 15000, 300, 0)
    t = text(view(dom(base, f"plan?b={b['id']}&sale=100000&buy=70000&aloan=30000&bloan=20000&cash=15000&move=300&tax=0")))
    grid = t[t.find("A \\ B"):]
    for a in (.95, 1, 1.05):
        for bb in (.95, 1, 1.05):
            g = gap(round(100000 * a), round(70000 * bb), *args, area); s = ("-" if g > 0 else "+") + won(abs(g)); assert s in grid, s


def test_pickers_open(base):
    h = dom(base, "home?sheet=pick-a"); assert 'id="sheet" class="on"' in h and h.count('data-pick="a:') == 40
    assert 'id="sheet" class="on"' in dom(base, "home?sheet=pick-b")


def test_dark_theme_and_settings(base):
    t = text(view(dom(base, "settings", "nosplash&theme=dark&nomotion")))
    assert "2026-08-31" in t and "6,251개" in t and "2016-10 ~ 2026-10" in t and "화면 테마" in t and "내 정보 초기화" in t


def test_pick_commit_delete_reset_flow(base):
    html = chrome(["--virtual-time-budget=15000", "--dump-dom", f"{base}/__t.html"])
    out = re.search(r'<pre id="out">(.*?)</pre>', html, re.S).group(1)
    assert "ERR" not in out, out
    assert "A후보=래미안퍼스티지" in out and re.search(r"A칩=[1-9]", out)
    assert "래미안퍼스티지" in out.split("A뷰=")[1].split("\n")[0] and "15층" in out.split("바=")[1].split("\n")[0]
    assert "B카드=" in out and "삭제후B=" in out
    nb = int(re.search(r"B카드=(\d+)", out).group(1)); na = int(re.search(r"삭제후B=(\d+)", out).group(1)); assert na == nb - 1       # 후보 하나 삭제됨
    assert "예시=N" in out                                                                                                          # 직접 추가하면 예시 라벨이 사라짐
    assert "다산한양수자인리버파크" in out.split("초기화후=")[1]                                                                        # 초기화하면 기본 A로 복귀


def test_fallback_complex_is_labelled(base):
    t = text(view(dom(base, f"c/{FB['id']}"))); head = t.split("평형·층별")[0]
    assert "36개월" in head and "참고용" in head and "확실" not in head and not re.search(r"▲ 상승|▬ 주춤|▼ 하락", head)


def test_compare_numbers(base):
    b = BEXAMPLES[0]; a = MINE; ea = det(a)["est"]["98|2"]; db = det(b); eb = db["est"][f"{b['pa']}|1"]
    t = text(view(dom(base, f"cmp?b={b['id']}")))
    for c in (a, b): assert c["name"] in t and pct(c["trend"]["r"]) in t and f"{pct(c['trend']['lo'])} ~ {pct(c['trend']['hi'])}" in t
    assert won(ea[0]) in t and won(eb[0]) in t
    diff = abs(eb[0] - ea[0]); assert f"B가 A보다 {won(diff)} {'비싸요' if eb[0] >= ea[0] else '저렴해요'}" in t
    ha, hb = HIST["c"][a["id"]], HIST["c"][b["id"]]; s0 = next(i for i, v in enumerate(ha["p"]) if v is not None and hb["p"][i] is not None)
    last = lambda p: max(i for i, v in enumerate(p) if v is not None); e = min(last(ha["p"]), last(hb["p"]))
    assert f"{qn(s0)} = 100" in t and f"{qn(s0)} → {qn(e)}" in t
    for h in (ha, hb): assert pct(h["p"][e] / h["p"][s0] - 1) in t
    for h in (ha, hb): assert (pct(h["d"][2]) in t) if h["d"] else True
    assert 'id="chart10"' in view(dom(base, f"cmp?b={b['id']}"))


def test_own_profit_card(base):
    html = chrome(["--virtual-time-budget=15000", "--dump-dom", f"{base}/__t.html?own"])
    out = re.search(r'<pre id="out">(.*?)</pre>', html, re.S).group(1); assert "ERR" not in out, out
    d = det(MINE); e = d["est"]["98|2"][0]; pts = d["series"]["pts"]; k = 12                      # 취득월 = 기준일 12개월 전(2025-08)
    card = out.split('지운후=')[0]; assert f"취득가 {won(95000)} · 2025.08" in card and pct(e / 95000 - 1) in card and pct(pts[24][1] / pts[24 - k][1] - 1) in card
    assert "내 집 수익 보기" in out.split("지운후=")[1]                                              # 입력 지우면 안내문으로 복귀


def test_stale_saved_examples_are_replaced(base):
    """이전 버전이 저장해 둔 예시(sample)가 localStorage에 남아 있어도 새 고정 예시로 바뀌어야 한다."""
    stale = BEXAMPLES[0]["id"].replace(BEXAMPLES[0]["id"], next(c["id"] for c in C if c["name"] == "주공1"))
    html = chrome(["--virtual-time-budget=15000", "--dump-dom", f"{base}/__t.html?stale={stale}"])
    out = re.search(r'<pre id="out">(.*?)</pre>', html, re.S).group(1); assert "ERR" not in out, out
    assert "벽산블루밍" in out and "한진한화그랑빌" in out and "주공1" not in out, out


def test_plan_rule_notes(base):
    b = BEXAMPLES[0]; q = lambda **k: "plan?b=" + b["id"] + "".join(f"&{a}={v}" for a, v in k.items())
    t = text(view(dom(base, q(sale=130000, buy=100000, bloan=70000)))); assert "12억을 넘어요" in t and "상한(참고)을 넘어요" in t and f"상한 {won(60000)}" in t
    t = text(view(dom(base, q(sale=100000, buy=200000, bloan=30000)))); assert "12억 이하예요" in t and "상한(참고)을 넘어요" not in t and f"상한 {won(40000)}" in t
    t = text(view(dom(base, q(sale=100000, buy=300000, bloan=10000)))); assert f"상한 {won(20000)}" in t


def tip_scenario(base, cid, m):
    html = chrome(["--virtual-time-budget=15000", "--dump-dom", f"{base}/__t.html?tip={m}&id={cid}"])
    out = re.search(r'<pre id="out">(.*?)</pre>', html, re.S).group(1); assert "ERR" not in out, out; return out


def test_chart_tooltip_shows_trade_and_trend(base):
    d = det(MINE); X = lambda m: 40 + 310 * (m + 24) / 24
    dots = [x for x in d["scatter"] if x[2] == 98]
    solo = next(x for x in dots if all(y is x or abs(X(y[0] / 30.4) - X(x[0] / 30.4)) > 14 for y in dots) and x[0] / 30.4 > -23)    # 다른 점과 충분히 떨어진 거래
    out = tip_scenario(base, MINE["id"], solo[0] / 30.4)
    date_ = __import__("datetime").date.fromordinal(IDX["meta"]["end_ord"] + solo[0]).isoformat()
    assert f"거래 {won(solo[1])}" in out and date_ in out and f"{solo[3]}층" in out, out
    m = next(k for k in range(-20, -2) if all(abs(X(k) - X(y[0] / 30.4)) > 12 for y in dots))                                       # 거래 점이 없는 위치 → 추세선 값
    s = d["series"]; e = d["est"]; mref = next(t["m"] for t in d["types"] if t["a"] == s["ref"])
    k = e["98|2"][0] / e[f"{s['ref']}|{s['tier']}"][0]; pt = next(p for p in s["pts"] if p[0] == m)
    out = tip_scenario(base, MINE["id"], m); assert f"추세선 {won(pt[1] * mref * k)}" in out and f"{won(pt[2] * mref * k)} ~ {won(pt[3] * mref * k)}" in out, out


def test_detail_trend_breakdown_and_history_card(base):
    t = text(view(dom(base, f"c/{MINE['id']}"))); m = MINE["trend"]
    assert f"최근 6개월 속도 {pct(m['b'])}와 최근 12개월 추세 {pct(m['c'])}의 평균이에요. 24개월 평균은 {pct(m['a'])}".replace(" ", "") in t.replace(" ", "")
    hd = HIST["c"][MINE["id"]]; p = hd["p"]; li = max(i for i, v in enumerate(p) if v is not None); mx = max(v for v in p if v is not None); mi = p.index(mx)
    assert f"10년 가격 흐름 · {hd['ref']}㎡ 기준" in t and f"{qn(mi)} · {won(mx)}" in t
    assert f"최근 분기({qn(li)}) {won(p[li])} (최고 대비 {pct(p[li] / mx - 1)})" in t
    if hd["d"]:
        pk, tr, dd, rec = hd["d"]
        assert (f"고점({pk}) 이후 더 낮아진 분기가 없었어요" in t) if dd == 0 else (f"{pct(dd)}" in t and f"{pk} → {tr}" in t)
    assert 'id="chart10"' in view(dom(base, f"c/{MINE['id']}"))


def test_reference_only_complex_gets_no_direction_label(base):
    t = text(view(dom(base, f"c/{REF24['id']}"))); head = t.split("평형·층별")[0]
    assert "참고용 · 최근 거래 적음" in head and "24개월 평균" in head and not re.search(r"▲ 상승|▬ 주춤|▼ 하락", head)
    assert "항상 추정" in head


# ---- 조건으로 후보 찾기: 화면(JS)과 무관한 독립 구현 ----
def annuity(rate, yrs):
    i, n = rate / 12, yrs * 12; return 12 * (i / (1 - (1 + i) ** -n) if i else 1 / n)


def loan_limit(buy, sgg, P):
    rg = RULES["regions"].get(str(sgg), {}); by_ltv = math.floor(buy * (RULES["ltv"]["regulated"] if rg.get("reg") else RULES["ltv"]["other"]))
    cap = next(c for lim, c in RULES["loan_cap"] if lim is None or buy <= lim)
    dsr = math.floor(max(0, RULES["dsr"]["limit"] * P["income"] - P["debt"]) / annuity(P["rate"] / 100 + RULES["dsr"]["stress"], P["yrs"])) if P["income"] > 0 else math.inf
    loan = min(by_ltv, cap, dsr)
    return loan, ("DSR" if dsr <= by_ltv and dsr <= cap and dsr != math.inf else "상한" if cap <= by_ltv else "LTV")


def need_for(buy, area, sgg, P, mode):
    r = lambda x: math.floor(x + .5)
    base = buy + r(buy * acq(buy, area)) + r(bro(buy)) + r(buy * .003) + P["move"]
    if mode == "gap": return base - r(buy * P["jr"] / 100) + P["rent"], 0
    loan, _ = loan_limit(buy, sgg, P); return base - loan, loan


def budget(P): return P["sale"] - P["aloan"] - math.floor(bro(P["sale"]) + .5) - P["tax"] + P["cash"]


def max_buy(B, area, sgg, P, mode):
    lo, hi = 0.0, 400000.0
    for _ in range(60):
        m = (lo + hi) / 2
        if need_for(math.floor(m + .5), area, sgg, P, mode)[0] <= B: lo = m
        else: hi = m
    return math.floor(lo)


def cls_of(est, area, sgg, P, mode, B):
    n = lambda v: need_for(math.floor(v + .5), area, sgg, P, mode)[0]
    return "가능" if n(est[2]) <= B else "빠듯" if n(est[0]) <= B else "불가"


A_AREA = next(t["m"] for t in det(MINE)["types"] if t["a"] == 98); A_SALE = det(MINE)["est"]["98|2"][0]
DEFP = dict(sale=A_SALE, aloan=0, tax=0, cash=0, move=300, income=0, debt=0, rate=RULES["dsr"]["rate"], yrs=RULES["dsr"]["years"], jr=60, rent=0)


def expected_rows(locs, P, mode, rng=15):
    out = []
    for cid, rows in CAND.items():
        c = next((x for x in C if x["id"] == cid), None)
        if not c or not any(l == str(c["sgg"]) or l == f"{c['sgg']}:{c['umd']}" for l in locs): continue
        cand = [t for t in rows if not rng or abs(t[2] - A_AREA) <= rng]
        if not cand: continue
        b = min(cand, key=lambda t: abs(t[2] - A_AREA)); tohu = RULES["regions"].get(str(c["sgg"]), {}).get("tohu")
        out.append((c, b, "갭 불가" if mode == "gap" and tohu else cls_of(b[3:6], b[2], c["sgg"], P, mode, budget(P))))
    return out


SCEN = [("11350", dict(income=12000, cash=10000), "loan"), ("11350:월계동", dict(cash=0, aloan=60000), "loan"), ("11680,11710", dict(income=3000, cash=5000, aloan=20000), "loan"),
        ("11350,41360", dict(income=12000, cash=10000), "gap"), ("41360", dict(cash=30000, rent=20000, jr=70), "gap"), ("11650", dict(income=0, cash=20000), "loan"),
        ("41135", dict(income=15000, cash=20000), "loan"), ("41597,41173", dict(income=12000, cash=15000), "loan"),         # 수원·분당·안양·동탄(2026-10 확장)
        ("41113", dict(cash=30000, rent=20000, jr=70), "gap"), ("41117,41113", dict(cash=30000, jr=70), "gap")]           # 권선구는 비토허제(갭 계산), 영통구는 토허제(갭 불가)


@pytest.mark.parametrize("loc,over,mode", SCEN)
def test_find_summary_and_counts_match_independent_calc(base, loc, over, mode):
    P = dict(DEFP, **over); q = f"find?loc={loc}&mode={mode}&" + "&".join(f"{k}={v}" for k, v in over.items()) + "&cls=가능,빠듯,불가&tohu=1"
    t = text(view(dom(base, q))); B = budget(P)
    assert f"{won(B)}" in t
    rows = expected_rows(loc.split(","), P, mode); cnt = {k: sum(1 for r in rows if r[2] == k) for k in ("가능", "빠듯", "불가")}
    assert f"가능 {cnt['가능']} · 빠듯 {cnt['빠듯']} · 불가 {cnt['불가']}" in t, (cnt, t[t.find("살 수 있는"):][:80])
    for g in sorted({int(l.split(":")[0]) for l in loc.split(",")}):
        if mode == "gap" and RULES["regions"][str(g)].get("tohu"): continue
        m = max_buy(B, A_AREA, g, P, mode); assert any(f"최대 {won(m + d)}" in t for d in (-2, -1, 0, 1, 2)), (g, won(m))
    if mode == "loan" and P["income"] == 0: assert "DSR을 반영하지 못했어요" in t
    names = [r[0]["name"] for r in sorted((r for r in rows if r[2] != "갭 불가"), key=lambda r: (-r[0]["n12"],))][:3]
    assert all(n in t for n in names)                                                # 기본 정렬(12개월 거래 많은 순) 상위 단지가 보임


def test_find_sort_and_dedupe(base):
    P = dict(DEFP, income=12000, cash=10000); t = text(view(dom(base, "find?loc=11350&income=12000&cash=10000&sort=lo&cls=가능,빠듯,불가")))
    rows = [r for r in expected_rows(["11350"], P, "loan")]; low = sorted(rows, key=lambda r: (r[1][3], -r[0]["n12"]))[:3]
    pos = [t.find(r[0]["name"]) for r in low]; assert all(p >= 0 for p in pos) and pos == sorted(pos), (pos, [r[0]["name"] for r in low])    # 낮은 가격순
    assert len({(r[0]["id"]) for r in rows}) == len(rows)                                       # 단지당 한 줄


def test_tohu_gap_is_blocked_with_notice(base):
    t = text(view(dom(base, "find?loc=11350&mode=gap&income=12000&cash=30000")))
    assert "토지거래허가구역은 전세 낀 매수(갭투자)를 할 수 없다고 보고 계산해요" in t and "2년 실거주 의무" in t and "갭투자 불가" in t
    assert "가능 0 · 빠듯 0 · 불가 0" in t and "조건에 맞는 단지가 없어요" in t                                   # 노원구는 전부 토허제 → 결과 없음
    t2 = text(view(dom(base, "find?loc=11350&mode=gap&income=12000&cash=30000&tohu=1")))
    assert "갭 불가" in t2 and "토지거래허가구역: 2년 실거주 의무로 갭투자 불가" in t2 and "후보에 추가" not in t2.split("살 수 있는 단지")[1]
    assert "토지거래허가구역은" not in text(view(dom(base, "find?loc=41360&mode=gap&cash=30000")))                  # 다산(비토허제)은 안내 없음
    for sgg, tohu in (("41310", True), ("41450", True), ("41360", False), ("11110", True)): assert bool(RULES["regions"][sgg].get("tohu")) is tohu


def test_rules_staleness_warning(base):
    age = (__import__("datetime").date(2027, 2, 1) - __import__("datetime").date.fromisoformat(RULES["asof"])).days
    old = text(view(dom(base, "find?loc=11350", "nosplash&theme=light&nomotion&today=2027-02-01")))
    assert f"규칙 기준일이 {age}일 지났어요" in old
    fresh = text(view(dom(base, "find?loc=11350", "nosplash&theme=light&nomotion&today=2026-10-10")))
    assert "규칙 기준일이" not in fresh and "(기준일 2026-10-09)" in fresh


def test_plan_uses_income_for_loan_and_flags_tohu(base):
    b = BEXAMPLES[0]; db = det(b); eb = db["est"][f"{b['pa']}|1"][0]; P = dict(DEFP, income=9000, debt=500)
    html = dom(base, f"plan?b={b['id']}&income=9000&debt=500&sale=100000"); t = text(view(html))
    loan, bind = loan_limit(eb, b["sgg"], P); m = re.search(r'id="f-bloan"[^>]*value="(\d+)"', html); assert m and int(m.group(1)) == loan, (m and m.group(1), loan)
    assert f"{bind} 한도에 걸림" in t and "토지거래허가구역" in t and "전세 낀 매수(갭투자)는 사실상 어려워요" in t and "일시적 2주택" in t
    t2 = text(view(dom(base, f"plan?b={b['id']}&jeonse=70000&sale=100000")))
    assert "입력한 전세 승계는 이 계산에서 쓸 수 없다고 봤어요" in t2 and "− 전세 승계(갭)" in t2


def test_feasible_candidates_have_no_shortfall_in_plan(base):
    """수용 기준: '가능'으로 보인 단지를 자금 계획으로 열면 부족액이 없어야 한다(주담대·갭 모두)."""
    for q in ("find?loc=11350&income=12000&cash=10000&sort=hi", "find?loc=41360&mode=gap&cash=30000&rent=10000&sort=hi", "find?loc=11680&income=30000&cash=150000&cls=가능,빠듯&sort=hi"):
        html = chrome(["--virtual-time-budget=20000", "--dump-dom", f"{base}/__t.html?fp={q}"]); out = re.search(r'<pre id="out">(.*?)</pre>', html, re.S).group(1)
        assert "ERR" not in out, out
        lines = [l for l in out.split("\n") if l.startswith("카드")]; assert len(lines) >= 3, out                # 가능 카드가 최소 3개는 있는 시나리오여야 검증이 의미 있음
        for l in lines:
            if "가능" in l.split("|")[1]: assert "여유" in l.split("|")[2], l                                      # 부족이면 실패


def test_location_sheet_and_dong_selection(base):
    html = chrome(["--virtual-time-budget=15000", "--dump-dom", f"{base}/__t.html?loc=1"]); out = re.search(r'<pre id="out">(.*?)</pre>', html, re.S).group(1)
    assert "ERR" not in out, out
    sheet_txt = out.split("시트=")[1].split("\n")[0]
    assert sheet_txt.count("토허제") == 34 and "남양주시(다산동)" in sheet_txt and "노원구" in sheet_txt                    # 서울 25 + 구리·하남 + 수원 영통·장안·팔달 + 분당 + 동안 + 동탄 + 의왕 = 34곳이 토허제
    assert '"locs":["11350"]' in out.split("구선택=")[1].split("\n")[0] and "11350:" in out.split("동선택=")[1].split("\n")[0]
    assert "노원구 " in out.split("요약=")[1]


def test_home_and_fab_lead_to_finder(base):
    assert "조건으로 후보 찾기" in text(view(dom(base, "home")))
    html = chrome(["--virtual-time-budget=15000", "--dump-dom", f"{base}/__t.html?fab=1"]); out = re.search(r'<pre id="out">(.*?)</pre>', html, re.S).group(1)
    assert "ERR" not in out and "입지 고르고 조건으로 찾기" in out and "단지 이름으로 직접 검색" in out and "찾기화면=조건으로 후보 찾기" in out


def test_edit_saved_a_and_b_type_floor_and_detail_save(base):
    html = chrome(["--virtual-time-budget=25000", "--dump-dom", f"{base}/__t.html?edit=1"]); out = re.search(r'<pre id="out">(.*?)</pre>', html, re.S).group(1)
    assert "ERR" not in out, out
    L = {l.split("=", 1)[0]: l.split("=", 1)[1] for l in out.split("\n") if "=" in l}
    assert "평형·층 변경" in L["A메뉴"] and "다른 단지로 변경" in L["A메뉴"] and "취득 정보" in L["A메뉴"]
    assert "98*" in L["A칩"] and "112" in L["A칩"] and "층=9" in L["A칩"]                                    # 현재 값이 미리 선택·입력되어 있음
    assert "112㎡ · 3층" in L["A바"]
    a = json.loads(L["A저장"]); assert (a["type"], a["floor"], a["buy"], a["ym"]) == (112, 3, 95000, "2025-08")      # 같은 단지 편집은 취득 정보를 지우지 않음
    before, after = json.loads(L["B전"]), json.loads(L["B후"])
    assert [b["id"] for b in after] == [b["id"] for b in before] and len(after) == 2                        # 제자리 교체(순서·개수 유지)
    assert after[0]["tier"] == 2 and not after[0].get("sample") and after[1].get("sample") is True           # 편집한 후보만 예시에서 내 선택으로 바뀜
    assert "평형·층대 변경" in L["B메뉴"] and "삭제" in L["B메뉴"] and "*" in L["B칩"]
    changed = after[0]["type"]; assert changed != before[0]["type"] if before[0]["type"] else True
    want, saved = L["상세저장"].split(" ", 1); sv = json.loads(saved); assert sv["type"] == int(want) and not sv.get("sample") and L["저장후"] == "표시"
    assert L["상세저장상태"] in ("버튼있음", "저장됨")


def test_detail_shows_add_button_for_unsaved_complex_and_saved_note_for_a(base):
    other = next(c for c in C if c["n12"] >= 50 and c["id"] != MINE["id"] and c["id"] not in {b["id"] for b in BEXAMPLES} and CAND.get(c["id"]))
    assert "후보에 추가" in text(view(dom(base, f"c/{other['id']}")))
    assert "내 집으로 저장된 평형이에요" in text(view(dom(base, f"c/{MINE['id']}")))
    assert "내 집 평형을 112㎡로 저장" in text(view(dom(base, f"c/{MINE['id']}?t=112")))


def test_bad_inputs_do_not_break_plan_or_find(base):
    """검증에서 발견: 만기 0·음수 입력이 NaN/Infinity 또는 설명 없는 한도 0으로 번지면 안 된다."""
    b = BEXAMPLES[0]
    for q in (f"plan?b={b['id']}&sale=-50000&income=9000&yrs=0&rate=abc", "find?loc=11350&income=12000&cash=10000&yrs=0&debt=-500"):
        t = text(view(dom(base, q)))
        assert "NaN" not in t and "Infinity" not in t and "JS 오류" not in t, (q, t[:300])


AREA = json.loads((SITE / "data" / "area.json").read_text(encoding="utf-8")); AA = AREA["a"]
num = lambda v: str(int(v)) if float(v).is_integer() else str(v)


def test_area_view_shows_numbers_from_data(base):
    """관심 입지 화면의 숫자는 area.json 값과 같고, 비정상 값(NaN 등)이 없다."""
    k = "11350:월계동"; a = AA[k]; t = text(view(dom(base, f"area?loc={k}")))
    assert "노원구 월계동" in t and f"단지 {a['nc']}개" in t and f"{a['t12']:,}건" in t and f"단지당 12개월 거래 {num(a['per12'])}건" in t
    assert pct(a["t12"] / a["t12p"] - 1) in t and f"{a['t3']}건" in t
    if a["idx"]: assert pct(a["ch"][1]) in t and pct(a["ch"][0]) in t
    assert not re.search(r"NaN|Infinity|undefined", t), t[:200]
    assert "가격 추이" in t and "거래량 추이" in t and "과거 기록이며" in t


def test_area_default_is_my_dong_and_thin_dong_points_to_gu(base):
    t = text(view(dom(base, "area"))); assert "남양주시 다산동" in t                                        # 저장값이 없으면 내 집(A)의 동
    thin = next(k for k, a in AA.items() if ":" in k and a["idx"] is None and a["nc"] >= 3)
    t = text(view(dom(base, f"area?loc={thin}"))); assert "가격 추이는 내지 않았어요" in t and "최근 12개월 거래" in t and "보기" in t   # 얇은 동: 가격 추이는 생략, 환금성은 표시, 구·시로 안내
    assert not re.search(r"NaN|Infinity|undefined", t)


def test_area_selection_flow(base):
    html = chrome(["--virtual-time-budget=20000", "--dump-dom", f"{base}/__t.html?area=1"]); out = __import__("html").unescape(re.search(r'<pre id="out">(.*?)</pre>', html, re.S).group(1))
    assert "ERR" not in out, out
    assert '처음=["41360:다산동"]' in out and "월계동" in out.split("동시트=")[1].split("\n")[0]
    assert '선택=["41360:다산동","11350:월계동","11680"]' in out and "노원구 월계동" in out and "강남구" in out and '빼기후=["11350:월계동","11680"]' in out
    assert "비움=[]" in out and "관심 있는 동이나 구·시를 고르면" in out


PYK = 400 / 121
PY_ROUTES = ["home", f"c/{MINE['id']}", f"c/{BEXAMPLES[0]['id']}?range=1y", f"cmp?b={BEXAMPLES[0]['id']}", f"plan?b={BEXAMPLES[0]['id']}", "find?loc=11350&income=12000&cash=10000", "area?loc=41360:다산동,11350:월계동"]


@pytest.mark.parametrize("route", PY_ROUTES)
def test_pyeong_mode_shows_no_m2_numbers(base, route):
    """?unit=py 이면 어느 화면에도 '숫자㎡'가 남지 않고 평으로 표시된다."""
    t = text(view(dom(base, route, "nosplash&theme=light&nomotion&unit=py"))).split("적용한 규칙")[0]                # 규칙 카드의 법적 기준(85㎡)은 ㎡로 남는다
    assert not re.search(r"\d㎡", t), re.findall(r".{25}\d㎡", t)[:3]
    assert re.search(r"\d평", t) and "NaN" not in t


def test_pyeong_values_are_converted_from_m2(base):
    t = text(view(dom(base, f"c/{MINE['id']}", "nosplash&theme=light&nomotion&unit=py")))
    assert f"{98 / PYK:.1f}평 · 28건" in t and f"{112 / PYK:.1f}평 · 4건" in t           # 평형 칩(98㎡ 28건, 112㎡ 4건)
    t = text(view(dom(base, "area?loc=11350", "nosplash&theme=light&nomotion&unit=py"))); assert f"{84 / PYK:.1f}평 환산 시세" in t


def test_unit_toggle_button_switches_and_persists(base):
    html = chrome(["--virtual-time-budget=20000", "--dump-dom", f"{base}/__t.html?unit=1"]); out = __import__("html").unescape(re.search(r'<pre id="out">(.*?)</pre>', html, re.S).group(1))
    assert "ERR" not in out, out
    before, after, st_, back = (out.split(k + "=")[1].split("\n")[0] for k in ("전", "후", "설정", "복귀"))
    assert "98㎡" in before and before.endswith("|m2")
    assert f"{98 / PYK:.1f}평" in after and "98㎡" not in after and "|py|" in after
    assert "면적 단위" in st_ and "98㎡" in back and back.endswith("|m2")


def test_area_sheet_search(base):
    html = chrome(["--virtual-time-budget=20000", "--dump-dom", f"{base}/__t.html?asearch=1"]); out = __import__("html").unescape(re.search(r'<pre id="out">(.*?)</pre>', html, re.S).group(1))
    assert "ERR" not in out, out
    g = lambda k: out.split(k + "=")[1].split("\n")[0]
    assert "성남시 분당구 정자동" in g("정자") and "동" in g("정자")                                               # 동 이름으로 검색
    sel = g("선택후"); assert '["41360:다산동","41135:정자동"]' in sel and sel.endswith("|정자")                       # 선택해도 검색어와 입력칸이 유지됨
    assert "성남시 분당구 정자동" in g("성남정자")                                                                   # 여러 단어는 모두 포함돼야 함(공백 무시)
    assert g("분당").startswith("성남시 분당구 ✕") or "성남시 분당구 구·시" in g("분당")                                 # 구·시가 동보다 먼저
    assert "맞는 입지가 없어요" in g("없음") and "서울" in g("비움") and "성남시 분당구 정자동" in g("뷰")


# ---------- UX 개선(루프 1~3)을 고정하는 테스트 ----------
def test_plan_has_sticky_result_and_live_amount_text(base):
    """자금 계획: 결과 요약이 위에 고정되고(입력 중에도 보임), 입력 전 현금 기준임을 알리며, 입력칸 옆에 한글 금액이 보인다."""
    b = BEXAMPLES[0]; html = dom(base, f"plan?b={b['id']}&sale=100000&buy=120000"); v = view(html); t = text(v)
    assert 'id="pstick"' in v and "B로 갈아타려면 부족한 돈" in t and "보유 현금 입력 전(0원 기준)" in t
    assert 'data-fm="sale"' in v and "10억" in t and "A를 팔 때" in t and "B를 살 때" in t and "내 자금" in t
    assert "보유 현금 입력 전" not in text(view(dom(base, f"plan?b={b['id']}&sale=100000&buy=120000&cash=30000")))      # 현금을 넣으면 안내가 사라짐


def test_home_summary_card_matches_plan(base):
    """홈 맨 위 '갈아타기 한눈에' 요약이 자금 계획 화면과 같은 부족/여유 금액을 보여준다."""
    h = text(view(dom(base, "home"))); assert "A → B 갈아타기 한눈에" in h and "자금 계획 자세히" in h and "1 내 집 고르기 2 후보 비교 3 필요한 돈 확인" in h
    m = re.search(r"(부족한 돈|남는 돈) ([0-9억만 ,]+?) B에 필요한 돈", h); assert m, h[:400]
    b = BEXAMPLES[0]; p = text(view(dom(base, f"plan?b={b['id']}")))
    assert m.group(2).strip() in p                                                                          # 같은 금액이 자금 계획 결과에도 있다


def test_detail_has_next_action_on_top(base):
    t = text(view(dom(base, f"c/{BEXAMPLES[0]['id']}"))); assert "이 후보로 자금 계획" in t and "A와 비교" in t          # 후보로 담긴 단지: 다음 단계
    assert "조건으로 후보 찾기" in text(view(dom(base, f"c/{MINE['id']}")))                                       # 내 집: 후보 찾기로
    other = next(c for c in C if c["trend"] and c["trend"]["m"] == "E" and c["id"] not in {b["id"] for b in BEXAMPLES} and c["id"] != MINE["id"] and c["n12"] >= 30)
    assert "로 후보에 추가" in text(view(dom(base, f"c/{other['id']}")))                                          # 아직 후보가 아닌 단지: 추가 버튼


def test_find_filters_and_tohu_notice(base):
    v = view(dom(base, "find?loc=11350&income=12000&cash=10000")); t = text(v)
    assert '<select id="fsort"' in v and "정렬" in t and "보여줄 결과" in t and "더 정확하게 계산하려면" in t         # 정렬은 선택 상자, 핵심 입력 먼저
    assert "선택한 입지의 단지는 모두 토지거래허가구역" in t and 'chip reg">토허제' not in v                       # 전부 토허제면 카드마다 반복하지 않고 한 번만 안내
    assert "적용한 규칙" in t and "<details" in v                                                              # 긴 규칙 안내는 접힘


def test_keyboard_and_chart_accessibility(base):
    html = dom(base, "home"); v = view(html)
    assert re.search(r'class="card tap"[^>]*tabindex="0"[^>]*role="button"|role="button"[^>]*tabindex="0"', v)       # 카드 전체를 누르는 요소가 키보드로 닿음
    assert 'role="img"' in v and "aria-label" in v
    d = view(dom(base, f"c/{MINE['id']}")); assert 'role="img" aria-label="가격 흐름 그래프"' in d and "점선은 거래가 모자라" in d    # 끊긴 구간을 점선으로 잇고 설명


def test_area_compare_table_and_rank_percent(base):
    t = text(view(dom(base, "area?loc=41360:다산동,41135:정자동")))
    assert "한눈에 비교" in t and "12개월 변화" in t and "하락기 낙폭" in t and "단지당 거래" in t and "(상위 " in t
    assert "한눈에 비교" not in text(view(dom(base, "area?loc=41360:다산동")))                                    # 한 곳만 고르면 비교 표 없음


def test_settings_has_glossary_after_unit_and_theme(base):
    t = text(view(dom(base, "settings"))); assert t.index("면적 단위") < t.index("화면 테마") < t.index("용어 설명") < t.index("데이터 기준")
    assert "가능·빠듯·불가" in t and "환금성" in t and "중간값" in t


# ---------- 온보딩 가이드 ----------
def _out(base, q):
    html = chrome(["--virtual-time-budget=40000", "--dump-dom", f"{base}/__t.html?{q}"]); return __import__("html").unescape(re.search(r'<pre id="out">(.*?)</pre>', html, re.S).group(1))


def test_tour_opens_by_param_and_has_five_steps(base):
    html = dom(base, "home", "nosplash&theme=light&nomotion&tour=1")
    assert re.search(r'<div id="sheet" class="on"[^>]*>', html) and re.search(r'id="sh-h">사용 가이드 1/5<', html)          # 시트가 열려 있고 제목이 1/5
    t = text(html); assert "갈아탈 때 필요한 걸 한곳에서 봐요" in t and "건너뛰기" in t and "투자 권유가 아니고" in t


def test_tour_flow_steps_replay_escape_and_links(base):
    out = _out(base, "tourflow=1"); assert "ERR" not in out, out
    g = lambda k: out.split(k + "=")[1].split("\n")[0]
    titles = ["갈아탈 때 필요한 걸 한곳에서 봐요", "먼저 내 집(A)과 후보(B)를 정해요", "숫자는 이렇게 읽어요", "후보와 입지를 둘러봐요", "마지막으로 필요한 돈을 확인해요"]
    for i, ti in enumerate(titles): assert f"사용 가이드 {i + 1}/5|{ti}|" in g(f"단계{i}"), (i, g(f"단계{i}"))
    assert g("단계0").endswith("다음") and g("단계4").endswith("시작하기")                                           # 마지막 단계만 '시작하기'
    assert g("끝") == "false"                                                                                       # 시작하기 → 닫힘
    assert g("다시").startswith("사용 가이드 1/5") and g("다시").endswith("true")                                    # 설정에서 다시 열기
    assert g("Esc") == "false"                                                                                      # Esc 로 닫힘
    assert "#/find" in g("링크") and g("링크").endswith("false")                                                    # 단계 4의 줄을 누르면 해당 화면으로 이동하고 가이드는 닫힘


def test_tour_autostarts_once_for_first_visit(base):
    out = _out(base, "tourauto=1"); assert "ERR" not in out, out
    g = lambda k: out.split(k + "=")[1].split("\n")[0]
    assert g("첫방문").startswith("true|사용 가이드 1/5") and g("첫방문").endswith("|1")                              # 처음 방문: 자동으로 뜨고 저장됨
    assert g("닫힘") == "false" and g("재방문") == "false"                                                           # 다시 방문하면 뜨지 않음


def test_tour_entrypoints_on_home_and_settings(base):
    assert "사용 가이드" in text(view(dom(base, "home"))) and 'data-act="tour:0"' in view(dom(base, "home"))
    t = text(view(dom(base, "settings"))); assert "사용 가이드 다시 보기" in t and t.index("화면 테마") < t.index("사용 가이드") < t.index("용어 설명")



def test_data_requests_carry_asset_version(base):
    """호스팅이 캐시 헤더를 못 바꿔도 갱신된 데이터가 보이도록, 모든 데이터 요청에 index.html 의 ?v= 가 붙는다."""
    v = re.search(r'app\.js\?(v=\d+)', (SITE / "index.html").read_text(encoding="utf-8")).group(1)
    out = _out(base, f"dv=1&id={MINE['id']}"); assert "ERR" not in out, out
    urls = json.loads(out.split("데이터요청=")[1].split("\n")[0])
    kinds = {u.split("?")[0].split("/")[1].split(".")[0] for u in urls}
    assert {"index", "rules", "cand", "hist", "area", "c"} <= kinds, kinds                                         # 홈·찾기·입지·상세에서 쓰는 데이터를 모두 읽음
    assert urls and all(u.endswith("?" + v) for u in urls), [u for u in urls if not u.endswith("?" + v)][:3]
