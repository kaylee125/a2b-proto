(() => {
'use strict';
const APP_NAME = '갈아탈까';
window.addEventListener('error', e => { const p = document.createElement('pre'); p.id = 'err'; p.textContent = 'JS 오류: ' + e.message + ' (줄 ' + (e.lineno || '?') + ')'; document.body.appendChild(p); });
const $ = (s, el = document) => el.querySelector(s);
const DV = ((document.currentScript || {}).src || '').split('?')[1] || '', dq = u => DV ? u + '?' + DV : u;   // index.html 의 ?v= 를 데이터 요청에도 붙여, 헤더를 못 바꾸는 호스팅에서도 갱신된 데이터가 바로 보이게 함
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const KEY = 'a2b.v1', DEF = () => ({ a: null, bs: null, plan: {}, theme: 'auto', areas: null, unit: 'm2', tour: 0 });
const store = { get() { try { return JSON.parse(localStorage.getItem(KEY) || '{}'); } catch (e) { return {}; } }, set(v) { try { localStorage.setItem(KEY, JSON.stringify(v)); } catch (e) {} } };
let st = Object.assign(DEF(), store.get());
const save = () => store.set(st);
const applyTheme = () => { const q = (location.search.match(/theme=(light|dark)/) || [])[1], t = q || (st.theme !== 'auto' ? st.theme : ''); if (t) document.documentElement.dataset.theme = t; else delete document.documentElement.dataset.theme; if (/nomotion/.test(location.search)) document.documentElement.classList.add('nomotion'); };
applyTheme();

let IDX = null, BY = {}; const DET = {};
const det = async id => DET[id] || (DET[id] = await fetch(dq('data/c/' + id + '.json')).then(r => { if (!r.ok) throw new Error('data ' + r.status); return r.json(); }));

/* ---------- 표시 보조 ---------- */
const PYEONG = 400 / 121;                                                   // 1평 = 3.3058㎡
const unitOf = () => (location.search.match(/unit=(py|m2)/) || [])[1] || (st.unit === 'py' ? 'py' : 'm2');   // ?unit= 은 테스트용(저장 안 함)
const fa = (v, d) => unitOf() === 'py' ? (v / PYEONG).toFixed(1) + '평' : (d == null ? v : (+v).toFixed(d)) + '㎡';   // 전용면적 표시(㎡ 또는 전용 환산 평)
const won = v => { if (!isFinite(v)) return '-'; const s = v < 0 ? '-' : '', a = Math.abs(Math.round(v)), e = Math.floor(a / 1e4), m = a % 1e4; return s + (e ? e + '억' + (m ? ' ' + m.toLocaleString('ko-KR') + '만' : '') : m.toLocaleString('ko-KR') + '만'); };
const pct = (r, d = 1) => (r >= 0 ? '+' : '-') + Math.abs(r * 100).toFixed(d) + '%';
const dateOf = o => new Date((o - 719163) * 864e5).toISOString().slice(0, 10);
const SK = { 상승: ['up', '▲'], 주춤: ['flat', '▬'], 하락: ['down', '▼'] };
const badge = t => t && t.m !== 'E' ? '<span class="badge na">참고용 · 최근 거래 적음</span>' : t ? `<span class="badge ${SK[t.s][0]}">${SK[t.s][1]} ${t.s}<span style="font-weight:600;font-size:11px;opacity:.85">${t.sure ? '확실' : '추정'}</span></span>` : '<span class="badge na">표본 부족</span>';
const tierOf = (d, floor) => !d.tiers ? 0 : floor < d.tiers[0] ? 0 : floor < d.tiers[1] ? 1 : 2;
const TIER = ['저층', '중층', '고층'];
const typeOf = (ref, d) => { const ts = d.types.map(t => t.a); if (ref.type != null && ts.includes(ref.type)) return ref.type; if (!ts.length) return null; return ref.role === 'a' ? ts.reduce((p, c) => Math.abs(c - 98) < Math.abs(p - 98) ? c : p) : ts[0]; };
const estOf = (d, a, tier) => d.est[a + '|' + tier] || d.est[a + '|' + (d.tiers ? 1 : 0)] || null;
const tierFor = (ref, d) => ref.role === 'a' ? tierOf(d, ref.floor ?? 9) : (d.tiers ? (ref.tier ?? 1) : 0);
const typeM = (d, a) => (d.types.find(t => t.a === a) || {}).m;
const monthsAgo = ym => { const [y, m] = ym.split('-').map(Number), e = new Date((IDX.meta.end_ord - 719163) * 864e5); return (e.getUTCFullYear() - y) * 12 + e.getUTCMonth() + 1 - m; };
function ownHtml(x) {
  const a = st.a, e = x.est;
  if (!a.buy) return `<div class="rel tap" data-act="own"><b>내 집 수익 보기</b> · 취득가를 입력하면 지금 추정 시세와 비교해 줘요 ›</div>`;
  if (!e) return '';
  const g = e[0] / a.buy - 1, k = a.ym ? monthsAgo(a.ym) : null, p = x.d.series && k != null && k >= 0 && k <= 24 ? x.d.series.pts[24 - k] : null, now = x.d.series ? x.d.series.pts[24] : null;
  return `<div class="rel tap" data-act="own"><div class="row"><span>취득가 ${won(a.buy)}${a.ym ? ' · ' + a.ym.replace('-', '.') : ''}</span><b class="${g >= 0 ? 'up' : 'down'}">${pct(g)} (${g >= 0 ? '+' : '-'}${won(Math.abs(e[0] - a.buy))})</b></div><div class="small muted" style="margin-top:4px">추정 시세 중간값 ${won(e[0])} 기준${p && p[1] > 0 && now ? ` · 같은 기간 이 단지 흐름 <b>${pct(now[1] / p[1] - 1)}</b>` : ''} · 수정하려면 눌러요</div></div>`;
}
function ownSheet() {
  const a = st.a; sheet('내 집 취득 정보', `<p class="note">이 기기에만 저장돼요. 시세 비교용이라 세금 계산과는 무관해요.</p><div class="lbl">취득가 (만원)</div><input class="fld" id="ob" inputmode="numeric" placeholder="예: 105000" value="${a.buy || ''}"><div class="lbl">취득월</div><input class="fld" id="oy" type="month" value="${a.ym || ''}" max="${IDX.meta.end.slice(0, 7)}"><button class="cta" data-act="own-save" style="width:100%;margin-top:10px"><b>저장</b></button><button class="act danger" data-act="own-clear">입력 지우기</button>`);
}

/* ---------- SVG ---------- */
function spark(d) {
  if (!d.series) return '';
  const p = d.series.pts, W = 300, H = 46, lo = Math.min(...p.map(x => x[2])), hi = Math.max(...p.map(x => x[3])), X = i => 2 + (W - 4) * i / (p.length - 1), Y = v => 4 + (H - 8) * (1 - (v - lo) / (hi - lo || 1));
  const line = p.map((x, i) => (i ? 'L' : 'M') + X(i).toFixed(1) + ',' + Y(x[1]).toFixed(1)).join(''), band = p.map((x, i) => (i ? 'L' : 'M') + X(i).toFixed(1) + ',' + Y(x[3]).toFixed(1)).join('') + p.slice().reverse().map((x, i) => 'L' + X(p.length - 1 - i).toFixed(1) + ',' + Y(x[2]).toFixed(1)).join('') + 'Z';
  return `<svg class="spark" role="img" aria-label="최근 가격 흐름 미니 그래프" viewBox="0 0 ${W} ${H}" preserveAspectRatio="none"><path d="${band}" fill="var(--ln)" opacity=".13"/><path d="${line}" fill="none" stroke="var(--ln)" stroke-width="1.7"/></svg>`;
}
let CH = null, HP = null;
const hist = () => HP || (HP = fetch(dq('data/hist.json')).then(r => r.ok ? r.json() : null).catch(() => null));
const qlab = (h, i) => { const t = +h.q0.slice(0, 4) * 4 + (+h.q0[5] - 1) + i; return `${Math.floor(t / 4)}Q${t % 4 + 1}`; };
const lastIdx = p => { for (let i = p.length - 1; i >= 0; i--) if (p[i] != null) return i; return -1; };
function multiChart(h, lines, fmt, id = 'chart10') {                                       // 분기 지수 선그래프(거래가 모자란 분기는 끊어서 표시)
  const W = 360, H = 200, pl = 40, pr = 10, pt = 10, pb = 22, n = h.n, X = i => pl + (W - pl - pr) * i / (n - 1), vs = lines.flatMap(l => l.p.filter(v => v != null));
  const lo0 = Math.min(...vs), hi0 = Math.max(...vs), step = nice((hi0 - lo0) / 4 || 1), lo = Math.floor(lo0 / step) * step, hi = Math.ceil(hi0 / step) * step, Y = v => pt + (H - pt - pb) * (1 - (v - lo) / (hi - lo || 1));
  let g = ''; for (let v = lo; v <= hi + 1e-9; v += step) g += `<line x1="${pl}" x2="${W - pr}" y1="${Y(v).toFixed(1)}" y2="${Y(v).toFixed(1)}" class="gl"/><text x="${pl - 4}" y="${(Y(v) + 3).toFixed(1)}" class="ax" text-anchor="end">${fmt(v)}</text>`;
  for (let i = 0; i < n; i++) if (qlab(h, i).endsWith('Q1') && (+qlab(h, i).slice(0, 4)) % 2 === 0) g += `<text x="${X(i).toFixed(1)}" y="${H - 6}" class="ax" text-anchor="middle">${qlab(h, i).slice(2, 4)}</text>`;
  let bridged = false;
  lines.forEach(l => { let d = '', pen = false, dots = '', prev = -1, br = ''; l.p.forEach((v, i) => { if (v == null) { pen = false; return; } if (!pen && prev >= 0) { br += 'M' + X(prev).toFixed(1) + ',' + Y(l.p[prev]).toFixed(1) + 'L' + X(i).toFixed(1) + ',' + Y(v).toFixed(1); bridged = true; } d += (pen ? 'L' : 'M') + X(i).toFixed(1) + ',' + Y(v).toFixed(1); pen = true; prev = i; dots += `<circle cx="${X(i).toFixed(1)}" cy="${Y(v).toFixed(1)}" r="1.8" fill="${l.c}"/>`; }); g += (br ? `<path d="${br}" fill="none" stroke="${l.c}" stroke-width="1.4" stroke-dasharray="3 3" opacity=".6"/>` : '') + `<path d="${d}" fill="none" stroke="${l.c}" stroke-width="1.8"/>${dots}`; });
  return `<svg class="chart" id="${id}" role="img" aria-label="${id === 'chartA2' ? '거래량 추이 그래프' : '가격 추이 그래프'}" viewBox="0 0 ${W} ${H}">${g}</svg>${bridged ? '<div class="small muted" style="margin-top:2px">점선은 거래가 모자라 값이 없는 구간을 이은 선이에요.</div>' : ''}`;
}
function defenseRows(h, hd) {
  if (!hd.d) return '<div class="kv"><span>2022~23 하락기</span><b>이 구간 거래가 모자라 계산하지 못했어요</b></div>';
  const [pk, tr, dd, rec] = hd.d, g = h.gu[hd.gu];
  if (dd === 0) return `<div class="kv"><span>2022~23 하락기</span><b>고점(${pk}) 이후 더 낮아진 분기가 없었어요</b></div>`;
  return `<div class="kv"><span>하락기 낙폭</span><b class="${dd < 0 ? 'down' : ''}">${pct(dd)}</b></div><div class="kv"><span>고점 → 저점</span><b>${pk} → ${tr}</b></div><div class="kv"><span>고점 회복</span><b>${rec != null ? `저점 후 ${rec}분기 만에 회복` : '데이터 기준 아직 회복 전'}</b></div>` + (g ? `<div class="kv"><span>${esc(hd.gu)} 단지 중위 낙폭</span><b>${pct(g.med)} (${g.n}개)</b></div>` : '');
}
const nice = v => { const p = Math.pow(10, Math.floor(Math.log10(v))), f = v / p; return (f <= 1 ? 1 : f <= 2 ? 2 : f <= 5 ? 5 : 10) * p; };
function chart(d, a, tier, months) {
  const s = d.series; if (!s) return '<p class="note">추세를 계산하지 못해 차트를 그리지 않았어요.</p>';
  const mRef = typeM(d, s.ref), e0 = estOf(d, s.ref, s.tier), e1 = estOf(d, a, tier);
  const sc = e0 && e1 ? e1[0] / e0[0] : 1;                                   // 시계열은 기준 타입·중간층 → 선택 타입·층대로 비율 환산
  const pts = s.pts.filter(x => x[0] >= -months).map(x => [x[0], x[1] * mRef * sc, x[2] * mRef * sc, x[3] * mRef * sc]);
  const dots = d.scatter.filter(x => x[2] === a && x[0] / 30.4 >= -months).map(x => [x[0] / 30.4, x[1]]);
  const W = 360, H = 220, pl = 40, pr = 10, pt = 14, pb = 24, X = m => pl + (W - pl - pr) * (m + months) / months;
  const vs = pts.flatMap(x => [x[2], x[3]]).concat(dots.map(x => x[1])), lo0 = Math.min(...vs), hi0 = Math.max(...vs), step = nice((hi0 - lo0) / 3 || 1000), lo = Math.floor(lo0 / step) * step, hi = Math.ceil(hi0 / step) * step, Y = v => pt + (H - pt - pb) * (1 - (v - lo) / (hi - lo || 1));
  let g = ''; for (let v = lo; v <= hi + 1; v += step) g += `<line x1="${pl}" x2="${W - pr}" y1="${Y(v).toFixed(1)}" y2="${Y(v).toFixed(1)}" class="gl"/><text x="${pl - 4}" y="${(Y(v) + 3).toFixed(1)}" class="ax" text-anchor="end">${(v / 1e4).toFixed(1)}억</text>`;
  const band = pts.map((x, i) => (i ? 'L' : 'M') + X(x[0]).toFixed(1) + ',' + Y(x[3]).toFixed(1)).join('') + pts.slice().reverse().map(x => 'L' + X(x[0]).toFixed(1) + ',' + Y(x[2]).toFixed(1)).join('') + 'Z';
  g += `<path d="${band}" class="ar"/><path d="${pts.map((x, i) => (i ? 'L' : 'M') + X(x[0]).toFixed(1) + ',' + Y(x[1]).toFixed(1)).join('')}" class="ln"/>`;
  g += dots.map(x => `<circle cx="${X(x[0]).toFixed(1)}" cy="${Y(x[1]).toFixed(1)}" r="2.6" fill="var(--accent)" opacity=".8"/>`).join('');
  const end = new Date((IDX.meta.end_ord - 719163) * 864e5);
  for (let q = 0; q <= 3; q++) { const m = -months + months * q / 3, dd = new Date(end.getTime() + m * 30.4 * 864e5); g += `<text x="${X(m).toFixed(1)}" y="${H - 6}" class="ax" text-anchor="${q === 0 ? 'start' : q === 3 ? 'end' : 'middle'}">${String(dd.getUTCFullYear()).slice(2)}.${String(dd.getUTCMonth() + 1).padStart(2, '0')}</text>`; }
  CH = { W, pl, pr, months, X, pts, dots: d.scatter.filter(x => x[2] === a && x[0] / 30.4 >= -months).map(x => ({ m: x[0] / 30.4, dt: x[0], amt: x[1], fl: x[3] })) };
  return `<div class="chart-wrap"><svg class="chart" id="chart" role="img" aria-label="가격 흐름 그래프" viewBox="0 0 ${W} ${H}">${g}</svg><div class="tip" id="tip"></div></div><div class="legend"><span><i></i>추세선(24개월 평균)</span><span><i class="o"></i>실제 거래(${dots.length}건)</span><span>음영 = 90% 범위</span></div>`;
}

/* ---------- 라우터·크롬 ---------- */
const parse = () => { const [h, q = ''] = location.hash.replace(/^#\/?/, '').split('?'), [name, arg] = h.split('/'); return { name: name || 'home', arg, q: new URLSearchParams(q) }; };
const nav = h => { if (location.hash === h) render(); else location.hash = h; };
const ICON = { back: '<svg><use href="#i-back"/></svg>', chev: '<svg><use href="#i-chev"/></svg>' };
function bar(o) {
  const my = o.my ? `<div class="myreg" data-act="pick-a"><div><div class="lb">내 집 A</div><div class="nm">${esc(o.my.nm)}</div><div class="ad">${esc(o.my.ad)}</div></div>${ICON.chev}</div>` : o.sub ? `<div class="sub-bar">${esc(o.sub)}</div>` : '';
  $('#bar').innerHTML = `<div class="bar-top">${o.back ? `<button class="ibtn" data-act="back" aria-label="뒤로">${ICON.back}</button>` : '<svg class="logo"><use href="#i-logo"/></svg>'}<div class="t">${esc(o.title)}</div><div class="unit" role="group" aria-label="면적 단위"><button data-act="unit:m2" class="${unitOf() === 'py' ? '' : 'on'}">㎡</button><button data-act="unit:py" class="${unitOf() === 'py' ? 'on' : ''}">평</button></div></div>${my}`; a11y($('#bar'));
}
const setTabs = n => document.querySelectorAll('#tabs button').forEach(b => b.classList.toggle('on', b.dataset.go === '#/' + n));
const a11y = root => root && root.querySelectorAll('[data-go]:not(button):not(a),[data-act]:not(button):not(a)').forEach(e => { if (!e.hasAttribute('tabindex')) { e.tabIndex = 0; e.setAttribute('role', 'button'); } });   // 카드·줄 전체를 누르는 요소도 키보드로 닿게
const sheet = (h, b) => { $('#sh-h').textContent = h; $('#sh-b').innerHTML = b; a11y($('#sh-b')); $('#sheet').classList.add('on'); $('#bd').classList.add('on'); };
const closeSheet = () => { $('#sheet').classList.remove('on'); $('#bd').classList.remove('on'); };

/* ---------- 상태 해석 ---------- */
const EXAMPLES = [['관악구', '벽산블루밍'], ['노원구', '한진한화그랑빌']];             // 첫 실행 예시 후보(85㎡) 고정: 데이터를 갱신해도 예시가 바뀌지 않게
function exampleBs(A) {
  const fixed = EXAMPLES.map(([gu, nm]) => IDX.c.find(c => c.gu === gu && c.name === nm && c.pa === 85)).filter(Boolean);
  if (fixed.length === EXAMPLES.length) return fixed;                                           // 단지가 데이터에 없으면 아래 규칙으로 대체                                                   // 갈아타기 예시: A보다 15~60% 비싼(상급지 이동) 거래 활발한 74~115㎡ 단지, 서로 다른 구
  const base = A && A.px, ok = c => c.trend && c.trend.w === 24 && c.px && c.pa >= 74 && c.pa <= 115 && c.n12 >= 30 && c.id !== (A || {}).id && (!base || (c.px >= base * 1.15 && c.px <= base * 1.6));
  const l = IDX.c.filter(ok).sort((x, y) => y.n12 - x.n12), out = [];
  for (const c of l) if (out.length < 2 && !out.some(o => o.gu === c.gu)) out.push(c);
  return out;
}
function refs() {
  if (!st.a) { const m = IDX.c.find(c => c.sgg === 41360 && c.name.includes('한양수자인리버파크')); if (m) st.a = { id: m.id, type: null, floor: 9 }; }
  if (st.bs && st.bs.length && st.bs.every(b => b.sample)) st.bs = null;                       // 직접 고른 후보가 없으면 예시는 저장하지 않고 매번 최신 규칙으로 채움
  if (!st.bs) { st.bs = exampleBs(st.a && BY[st.a.id]).map(c => ({ id: c.id, type: c.pa, tier: 1, sample: true })); }
  return { a: st.a && BY[st.a.id] ? Object.assign({ role: 'a' }, st.a) : null, bs: st.bs.filter(b => BY[b.id]).map(b => Object.assign({ role: 'b' }, b)) };
}
async function resolve(ref) { const c = BY[ref.id], d = await det(ref.id), a = typeOf(ref, d), tier = tierFor(ref, d); return { ref, c, d, a, tier, est: a == null ? null : estOf(d, a, tier), m: a == null ? null : typeM(d, a) }; }

/* ---------- 화면: 홈 ---------- */
function rel(c) {
  const t = c.trend; if (!t) return '';
  if (t.m !== 'E') return `<div class="rel muted">최근 거래가 적어 상승·하락을 가르지 않고, 주변 단지와도 직접 비교하지 않아요.</div>`;
  const g = c.dong ? { lb: c.umd, ...c.dong } : c.guagg ? { lb: c.gu, ...c.guagg } : null;
  if (!g) return `<div class="rel muted">주변 비교는 같은 동·구에서 추세를 낸 단지가 6개 이상일 때만 보여요.</div>`;
  const diff = (t.r - g.med) * 100;
  return `<div class="rel">${esc(g.lb)} ${g.n}개 단지의 중간값 <b>${pct(g.med)}</b> · 이 단지 <b>${pct(t.r)}</b> → 중간값보다 <b class="${diff >= 0 ? 'up' : 'down'}">${Math.abs(diff).toFixed(1)}%p ${diff >= 0 ? '높아요' : '낮아요'}</b> · ${g.n}개 중 ${g.rank}위</div>`;
}
function cardHtml(x, label) {
  const { c, d, ref } = x, t = c.trend, e = x.est;
  const body = t ? `<div class="hero-pct ${t.m !== 'E' ? '' : t.s === '상승' ? 'up' : t.s === '하락' ? 'down' : ''}">${pct(t.r)}<span class="small muted" style="font-weight:500"> ${t.m === 'E' ? '최근 6개월' : (t.w === 36 ? '36개월 평균' : '24개월 평균')}</span></div><div class="range">90% 범위 ${pct(t.lo)} ~ ${pct(t.hi)}${t.w === 36 ? ' · 36개월 기준' : ''}${t.m === 'A' && t.w === 24 ? ' · 24개월 평균' : ''}</div>` : `<div class="note" style="margin-top:8px">최근 36개월 거래가 20건에 못 미쳐 추세는 계산하지 않았어요. (전체 ${c.n}건)</div>`;
  const price = e ? `<div class="rc-r"><div class="lbl">추정 시세 · ${fa(x.a)}${d.tiers ? ' ' + (ref.role === 'a' ? ref.floor + '층' : TIER[x.tier]) : ''}</div><div class="big" style="font-size:21px">${won(e[0])}</div><div class="small muted">${won(e[1])} ~ ${won(e[2])}</div></div>` : '';
  return `<div class="card tap" data-go="#/c/${c.id}?t=${x.a ?? ''}"><div class="rc-top"><div><span class="chip" style="margin-bottom:4px">${label}</span><div class="rc-name">${esc(c.name)}<span class="s">${esc(c.gu)} ${esc(c.umd)} <span style="white-space:nowrap">· ${c.by}년</span></span></div></div>${ref.role === 'b' ? `<button class="kebab" data-act="kebab:${c.id}" aria-label="더보기">⋮</button>` : `<button class="kebab" data-act="kebab-a" aria-label="더보기">⋮</button>`}</div>
  <div class="rc-mid"><div>${badge(t)}${body}</div>${price}</div>${spark(d)}${rel(c)}${ref.role === 'a' ? ownHtml(x) : ''}<div class="rc-foot"><span>최근 12개월 거래 ${c.n12}건</span><span>·</span><span>마지막 신고 ${c.last}일 전</span></div></div>`;
}
async function home() {
  const { a, bs } = refs(), xa = a && await resolve(a), xbs = await Promise.all(bs.map(resolve));
  bar({ title: APP_NAME, my: xa ? { nm: xa.c.name, ad: `${xa.c.gu} ${xa.c.umd} · ${xa.a == null ? '-' : fa(xa.a)}${xa.d.tiers ? ' · ' + a.floor + '층' : ''}` } : { nm: '내 집을 선택하세요', ad: '단지 이름으로 검색' } });
  await needRules();
  let h = st.intro ? '' : `<div class="card"><b>예시 단지로 채워져 있어요</b><div class="steps"><span><i>1</i>내 집 고르기</span><span><i>2</i>후보 비교</span><span><i>3</i>필요한 돈 확인</span></div><div class="note">내 집(A)과 후보(B)를 직접 고르면 내 상황에 맞는 추세와 자금 계획을 볼 수 있어요. 입력한 정보는 이 기기에만 저장돼요.</div><div class="row" style="margin-top:8px"><button class="chip tap" data-act="intro:pick" style="padding:8px 14px;font-size:13px;background:var(--fon-bg);color:var(--fon-ink)">내 집 고르기</button><button class="small muted" data-act="intro:ok">이대로 둘러보기</button></div></div>`;
  if (xa && xbs.length && xa.est && xbs[0].est) { const b0 = xbs[0], { p } = planInputs(xa, b0, new URLSearchParams()), R = calc(p), short = R.gap > 0;
    h += `<div class="card sumcard"><div class="lbl">A → B 갈아타기 한눈에 <span class="small muted">· 추정</span></div><div class="sum-route">${esc(xa.c.name)} → ${esc(b0.c.name)}</div><div class="sum-main"><span>${short ? '부족한 돈' : '남는 돈'}</span><b class="${short ? 'short' : 'surplus'}">${won(Math.abs(R.gap))}</b></div><div class="small muted">B에 필요한 돈 ${won(R.need)} · A 매도 후 ${won(R.proceeds)} + 보유 현금 ${won(p.cash)}${st.plan.cash == null ? ' <b>(현금 입력 전)</b>' : ''}</div><div class="row" style="margin-top:12px"><button class="chip tap sumbtn main" data-go="#/plan?b=${b0.c.id}">자금 계획 자세히 ›</button><button class="chip tap sumbtn" data-go="#/cmp?b=${b0.c.id}">A와 B 비교 ›</button></div></div>`; }
  if (xa) h += cardHtml(xa, '내 집 A'); else h += `<div class="card tap" data-act="pick-a"><b>내 집(A)을 선택하세요</b><div class="note">단지 이름·동으로 검색해 평형과 층을 고르면 추세와 시세 범위를 보여줘요.</div></div>`;
  h += `<div class="sec"><b>갈아타기 후보 B</b><span>${xbs.length}개</span></div>`;
  h += xbs.map(x => cardHtml(x, '후보 B' + (x.ref.sample ? ' · 예시' : ''))).join('') || `<div class="card tap" data-act="pick-b"><b>후보 단지를 추가하세요</b><div class="note">오른쪽 아래 + 버튼으로도 추가할 수 있어요.</div></div>`;
  h += `<div class="cta tap" data-go="#/area" style="background:var(--card);color:var(--ink)"><div><b>관심 입지 보기</b><br><span>동·구 단위 가격 추이와 환금성을 봐요</span></div><span style="font-size:22px">›</span></div>`;
  if (xa) h += `<div class="cta tap" data-go="#/find" style="background:var(--card);color:var(--ink)"><div><b>조건으로 후보 찾기</b><br><span>입지를 고르면 내 자금으로 살 수 있는 단지를 보여줘요</span></div><span style="font-size:22px">›</span></div>`;
  if (xa && xbs.length) h += `<div class="cta tap" data-go="#/cmp?b=${xbs[0].c.id}" style="background:var(--card);color:var(--ink)"><div><b>A와 B 비교하기</b><br><span>추세·시세·주변 대비를 나란히 봐요</span></div><span style="font-size:22px">›</span></div>`;
  h += `<p class="note">추세 = 같은 단지 안에서 층·평형 차이를 보정한 실거래 회귀로 본 최근 6개월 변화율(최근 6개월 속도와 12개월 추세의 평균)이에요. 데이터 기준 ${esc(IDX.meta.end)}, 국토교통부 실거래 신고분. <button class="linkbtn" data-act="tour:0">사용 가이드</button> · <button class="linkbtn" data-go="#/settings">용어 설명 ›</button></p>`;
  return h;
}

/* ---------- 화면: 단지 상세 ---------- */
async function detail(id, q) {
  const c = BY[id]; if (!c) return '<div class="card">단지를 찾을 수 없습니다.</div>';
  refs();                                                                   // 주소로 바로 열어도 내 집(A)/예시 상태가 채워지도록
  const d = await det(id), isA = st.a && st.a.id === id, ref = { id, role: isA ? 'a' : 'b', type: q.get('t') ? +q.get('t') : null, floor: isA ? st.a.floor : null, tier: 1 };
  const x = await resolve(Object.assign({}, ref, isA ? { type: ref.type ?? st.a.type } : {})), t = c.trend, months = q.get('range') === '1y' ? 12 : 24;
  bar({ title: c.name, back: true, sub: `${c.gu} ${c.umd} · ${c.by}년 준공 · 거래 ${c.n}건` });
  let h = `<div class="card"><div class="row">${badge(t)}<span class="small muted">6개월 추세 · 기준 ${esc(IDX.meta.end)}</span></div>`;
  h += t ? `<div class="hero-pct ${t.m !== 'E' ? '' : t.s === '상승' ? 'up' : t.s === '하락' ? 'down' : ''}">${pct(t.r)}</div><div class="range">90% 범위 ${pct(t.lo)} ~ ${pct(t.hi)} · ${t.w === 36 ? '최근 24개월 거래가 적어 36개월 거래로 계산한 참고용 추정(주변 비교와 같은 기준이 아니에요)' : t.m === 'A' ? '최근 12개월 거래가 12건 미만이라 최근 변화를 반영하지 못한 24개월 평균 추세예요(항상 추정)' : t.sure ? '범위 전체가 같은 방향이라 확실' : '범위가 ±3% 기준에 걸쳐 있어 오르는지 내리는지 단정하기 어려운 추정'}</div>${t.m === 'E' ? `<div class="note" style="margin-top:6px">최근 6개월 속도 <b>${pct(t.b)}</b>와 최근 12개월 추세 <b>${pct(t.c)}</b>의 평균이에요. 24개월 평균은 ${pct(t.a)}예요.</div>` : ''}` : `<div class="note" style="margin-top:8px">최근 36개월 거래가 20건에 못 미쳐 추세를 계산하지 않았어요. 아래 시세는 최근 12개월 거래의 중위값이에요.</div>`;
  const bE = (st.bs || []).find(b => b.id === id), act0 = isA ? `<button class="chip tap act-main" data-go="#/find">조건으로 후보 찾기 ›</button>` : bE ? `<button class="chip tap act-main" data-go="#/plan?b=${id}">이 후보로 자금 계획 ›</button><button class="chip tap act-sub" data-go="#/cmp?b=${id}">A와 비교 ›</button>` : (x.a ? `<button class="chip tap act-main" data-act="fadd:${id}:${x.a}">${fa(x.a)}로 후보에 추가</button>` : '');
  h += rel(c) + (act0 ? `<div class="row act-row">${act0}</div>` : '') + '</div>';
  const bEnt = (st.bs || []).find(b => b.id === id), savedT = isA ? typeOf({ role: 'a', type: st.a.type }, d) : bEnt ? typeOf({ role: 'b', type: bEnt.type }, d) : null;
  const chipCss = 'padding:7px 14px;font-size:13px', saveBtn = !x.a ? '' : isA || bEnt ? (x.a !== savedT ? `<button class="chip tap" data-act="savetype:${id}:${x.a}" style="${chipCss}">${isA ? '내 집' : '후보'} 평형을 ${fa(x.a)}로 저장</button>` : `<span class="small muted">${isA ? '내 집으로' : '후보로'} 저장된 평형이에요</span>`) : '';
  if (d.types.length) {
    h += `<div class="card"><h3>평형·층별 시세 범위</h3><div class="chips">${d.types.map(tp => `<button class="${tp.a === x.a ? 'on' : ''}" data-go="#/c/${id}?t=${tp.a}&range=${months === 12 ? '1y' : '2y'}">${fa(tp.a)} · ${tp.n}건</button>`).join('')}</div>${saveBtn}`;
    if (d.tiers) h += `<div class="kvs">${[0, 1, 2].map(k => { const e = estOf(d, x.a, k); return e ? `<div class="kv"><span>${TIER[k]}${k === 0 ? ` (${d.tiers[0] - 1}층 이하)` : k === 1 ? ` (${d.tiers[0]}~${d.tiers[1] - 1}층)` : ` (${d.tiers[1]}층 이상)`}</span><b>${won(e[0])} <span class="small muted">(${won(e[1])} ~ ${won(e[2])})</span></b></div>` : ''; }).join('')}</div>`;
    else if (x.est) h += `<div class="kvs"><div class="kv"><span>전체 층</span><b>${won(x.est[0])} <span class="small muted">(${won(x.est[1])} ~ ${won(x.est[2])})</span></b></div></div>`;
    h += `<p class="note">범위는 "지금 이 평형·층의 거래 한 건"이 들어올 90% 구간이에요. ${d.est_kind === 'median' ? '표본이 적어 최근 12개월 거래의 중위값과 10~90% 분위로 대신했어요.' : ''}</p></div>`;
  }
  if (d.series) h += `<div class="card"><div class="row"><h3 style="margin:0">가격 흐름 · ${fa(x.a)}</h3><div class="filters" style="margin:0;padding:0">${[['1y', '1년'], ['2y', '2년']].map(([k, l]) => `<button class="${(months === 12) === (k === '1y') ? 'on' : ''}" data-go="#/c/${id}?t=${x.a}&range=${k}">${l}</button>`).join('')}</div></div>${chart(d, x.a, x.tier, months)}</div>`;
  const H = await hist(), hd = H && H.c[id];
  if (hd) { const li = lastIdx(hd.p), mx = Math.max(...hd.p.filter(v => v != null)), mi = hd.p.indexOf(mx);
    h += `<div class="card"><h3>10년 가격 흐름 · ${fa(hd.ref)} 기준</h3>${multiChart(H, [{ p: hd.p, c: 'var(--ln)' }], v => (v / 1e4).toFixed(1) + '억')}<div class="kvs"><div class="kv"><span>10년 최고 분기</span><b>${qlab(H, mi)} · ${won(mx)}</b></div><div class="kv"><span>최근 분기(${qlab(H, li)})</span><b>${won(hd.p[li])} (${hd.p[li] >= mx ? '10년 중 최고' : '최고 대비 ' + pct(hd.p[li] / mx - 1)})</b></div>${defenseRows(H, hd)}</div><p class="note">분기에 거래가 3건 이상일 때만 점을 찍고, 층·평형 구성 차이를 보정했어요. 과거 기록이며 같은 흐름이 반복된다는 뜻은 아니에요.</p></div>`; }
  h += `<div class="card"><h3>환금성</h3><div class="kvs"><div class="kv"><span>최근 12개월 신고 거래</span><b>${c.n12}건</b></div><div class="kv"><span>마지막 신고 거래</span><b>수집 기준 ${c.last}일 전</b></div><div class="kv"><span>${t && t.w === 36 ? 36 : 24}개월 추세 표본</span><b>${t ? t.n + '건' : '20건 미만'}</b></div></div><button class="chip tap" data-go="#/area?loc=${c.sgg}:${esc(c.umd)}" style="margin-top:10px;padding:7px 14px;font-size:13px">이 동의 가격 추이·환금성 보기</button></div>`;
  h += `<div class="card"><h3>최근 거래</h3><table class="tbl"><tr><th>계약일</th><th>전용</th><th>층</th><th>금액</th></tr>${d.recent.map(r => `<tr><td>${dateOf(r[0])}</td><td>${fa(r[2], 1)}</td><td>${r[3]}층</td><td><b>${won(r[1])}</b></td></tr>`).join('')}</table></div>`;
  h += `<p class="note">한계: 실거래 신고는 계약 후 최대 30일 늦게 반영돼 최근 두 달은 제외했어요. 같은 단지라도 동·향·수리 상태는 반영하지 않아요. 투자 판단 책임은 본인에게 있어요.</p>`;
  return h;
}

/* ---------- 화면: A↔B 비교 ---------- */
function cmpChart(sa, sb, na, nb) {
  if (!sa || !sb) return '<p class="note">두 단지 모두 가격 흐름을 계산한 경우에만 겹쳐 그려요.</p>';
  const A = sa.pts.map(x => x[1] / sa.pts[0][1] * 100), B = sb.pts.map(x => x[1] / sb.pts[0][1] * 100), all = A.concat(B), lo = Math.floor(Math.min(...all) / 5) * 5, hi = Math.ceil(Math.max(...all) / 5) * 5;
  const W = 360, H = 190, pl = 34, pr = 10, pt = 10, pb = 22, X = i => pl + (W - pl - pr) * i / 24, Y = v => pt + (H - pt - pb) * (1 - (v - lo) / (hi - lo || 1)), P = a => a.map((v, i) => (i ? 'L' : 'M') + X(i).toFixed(1) + ',' + Y(v).toFixed(1)).join('');
  let g = ''; for (let v = lo; v <= hi; v += 5) g += `<line x1="${pl}" x2="${W - pr}" y1="${Y(v).toFixed(1)}" y2="${Y(v).toFixed(1)}" class="gl"/><text x="${pl - 4}" y="${(Y(v) + 3).toFixed(1)}" class="ax" text-anchor="end">${v}</text>`;
  g += `<path d="${P(A)}" class="ln"/><path d="${P(B)}" fill="none" stroke="var(--accent)" stroke-width="1.8"/>`;
  return `<svg class="chart" id="chart" role="img" aria-label="가격 흐름 그래프" viewBox="0 0 ${W} ${H}">${g}</svg><div class="legend"><span><i></i>A ${esc(na)} ${(A[24] - 100).toFixed(1)}%</span><span><i class="o" style="border-top-style:solid"></i>B ${esc(nb)} ${(B[24] - 100).toFixed(1)}%</span></div>`;
}
async function cmp10(xa, xb) {
  const H = await hist(), ha = H && H.c[xa.c.id], hb = H && H.c[xb.c.id];
  if (!ha || !hb) return `<div class="card"><h3>최근 2년 가격 흐름 <span class="small muted">(24개월 전 = 100)</span></h3>${cmpChart(xa.d.series, xb.d.series, xa.c.name, xb.c.name)}<p class="note">10년 흐름은 두 단지 모두 거래가 충분할 때만 보여줘요.</p></div>`;
  const s = ha.p.findIndex((v, i) => v != null && hb.p[i] != null), la = lastIdx(ha.p), lb = lastIdx(hb.p), e = Math.min(la, lb), reb = p => p.map(v => v == null ? null : v / p[s] * 100);
  if (s < 0) return `<div class="card"><h3>10년 상대 흐름</h3><p class="note">두 단지의 거래가 겹치는 분기가 없어 비교하지 못했어요.</p></div>`;
  const ra = reb(ha.p), rb = reb(hb.p), row = (l, f) => `<tr><td>${l}</td><td>${f(ha, ra)}</td><td>${f(hb, rb)}</td></tr>`;
  return `<div class="card"><h3>10년 상대 흐름 <span class="small muted">(${qlab(H, s)} = 100)</span></h3>${multiChart(H, [{ p: ra, c: 'var(--ln)' }, { p: rb, c: 'var(--accent)' }], v => v.toFixed(0))}<div class="legend"><span><i></i>A ${esc(xa.c.name)}</span><span><i class="o" style="border-top-style:solid"></i>B ${esc(xb.c.name)}</span></div>
  <table class="tbl" style="margin-top:8px"><tr><th></th><th>A</th><th>B</th></tr>${row(qlab(H, s) + ' → ' + qlab(H, e), (x, r) => `<b>${pct(r[e] / 100 - 1)}</b>`)}${row('하락기 낙폭', x => x.d ? pct(x.d[2]) : '-')}${row('고점 회복', x => x.d ? (x.d[3] != null ? x.d[3] + '분기' : '전') : '-')}</table>
  <p class="note">같은 시기에 두 단지가 얼마나 다르게 움직였는지 보는 그래프예요. 가격 수준은 위 표의 추정 시세로 비교하세요. 과거 기록이며 같은 흐름이 반복된다는 뜻은 아니에요.</p></div>`;
}
async function compare(q) {
  const { a, bs } = refs(); bar({ title: 'A와 B 비교', back: true });
  if (!a || !bs.length) return `<div class="card">홈에서 내 집(A)과 후보(B)를 먼저 고르세요.</div>`;
  const b = bs.find(x => x.id === q.get('b')) || bs[0], [xa, xb] = await Promise.all([resolve(a), resolve(b)]);
  const row = (l, f) => `<tr><td>${l}</td><td>${f(xa)}</td><td>${f(xb)}</td></tr>`, T = x => x.c.trend;
  const tabs = bs.length > 1 ? `<div class="chips">${bs.map(x => `<button class="${x.id === b.id ? 'on' : ''}" data-go="#/cmp?b=${x.id}">${esc(BY[x.id].name)}</button>`).join('')}</div>` : '';
  const rl = x => { const c = x.c, g = c.dong || c.guagg; return g && T(x) ? `${pct(T(x).r - g.med)}p · ${g.n}개 중 ${g.rank}위` : '-'; };
  return `${tabs}<div class="card"><h3>지금 상태</h3><table class="tbl"><tr><th></th><th>A 내 집</th><th>B 후보</th></tr>
  ${row('단지', x => `<b>${esc(x.c.name)}</b><br><span class="small muted">${esc(x.c.gu)} ${esc(x.c.umd)} · ${x.c.by}년</span>`)}
  ${row('상태', x => T(x) ? (T(x).m !== 'E' ? '참고용<br><span class="small muted">최근 거래 적음</span>' : `${SK[T(x).s][1]} ${T(x).s}<br><span class="small muted">${T(x).sure ? '확실' : '추정'}</span>`) : '표본 부족')}
  ${row('6개월 추세', x => T(x) ? `<b>${pct(T(x).r)}</b><br><span class="small muted">${pct(T(x).lo)} ~ ${pct(T(x).hi)}</span>` : '-')}
  ${row('주변 대비', rl)}
  ${row('추정 시세', x => x.est ? `<b>${won(x.est[0])}</b><br><span class="small muted">${fa(x.a)} ${x.d.tiers ? (x.ref.role === 'a' ? x.ref.floor + '층' : TIER[x.tier]) : ''}</span>` : '-')}
  ${row('환금성', x => `12개월 ${x.c.n12}건<br><span class="small muted">마지막 ${x.c.last}일 전</span>`)}</table>
  ${xa.est && xb.est ? `<div class="rel">B가 A보다 <b>${won(Math.abs(xb.est[0] - xa.est[0]))}</b> ${xb.est[0] >= xa.est[0] ? '비싸요' : '저렴해요'} (추정 시세 중간값 기준)</div>` : ''}</div>
${await cmp10(xa, xb)}
  <div class="cta tap" data-go="#/plan?b=${b.id}"><div><b>이 조합으로 자금 계획</b></div><span style="font-size:22px">›</span></div>
  <p class="note">표의 추정 시세는 각 단지의 선택한 평형·층 기준이에요. 평형이 다른 단지끼리도 흐름(변화율)은 비교할 수 있지만 가격 수준은 표의 시세로 비교하세요.</p>`;
}

/* ---------- 화면: 자금 계획 ---------- */
const BRO = [[5000, .006], [20000, .005], [90000, .004], [120000, .005], [150000, .006], [Infinity, .007]];
const broRate = v => BRO.find(r => v < r[0])[1];
const broFee = v => { const f = v * broRate(v); return v < 5000 ? Math.min(f, 25) : v < 20000 ? Math.min(f, 80) : f; };   // 서울시 조례 요율표(한도액 포함)
const r1 = Math.round;
function acqRate(buy, area) {                                              // 1주택(또는 일시적 2주택) 가정: 6억 이하 1%, 6~9억 구간식, 9억 초과 3% + 지방교육세 + (85㎡ 초과) 농특세 0.2%
  const base = buy <= 60000 ? 1 : buy <= 90000 ? buy / 1e4 * 2 / 3 - 3 : 3;
  return (base + base * .1 + (area > 85 ? .2 : 0)) / 100;
}
function calc(p) {
  const bs = r1(broFee(p.sale)), proceeds = p.sale - p.aloan - bs - p.tax;
  const acq = r1(p.buy * acqRate(p.buy, p.area)), bb = r1(broFee(p.buy)), legal = r1(p.buy * .003);
  const need = p.buy + acq + bb + legal + p.move - p.bloan - (p.jeonse || 0) + (p.rent || 0);
  return { bs, proceeds, acq, bb, legal, need, gap: need - proceeds - p.cash };
}
const gapHtml = g => g > 0 ? `<span class="res-big short">${won(g)} 부족</span>` : `<span class="res-big surplus">${won(-g)} 여유</span>`;
const gapCell = g => `<td class="${g > 0 ? 'short' : 'surplus'}">${g > 0 ? '-' : '+'}${won(Math.abs(g))}</td>`;
function planResult(c) {
  const { p, ea, eb } = c, R = calc(p), ra = ea ? [ea[1] / ea[0], ea[2] / ea[0]] : [.95, 1.05], rb = eb ? [eb[1] / eb[0], eb[2] / eb[0]] : [.95, 1.05];
  const sc = [['A 비싸게 팔고 B 싸게 사면', p.sale * ra[1], p.buy * rb[0]], ['중간 시세', p.sale, p.buy], ['A 싸게 팔고 B 비싸게 사면', p.sale * ra[0], p.buy * rb[1]]].map(([n, s, b]) => [n, r1(s), r1(b)]);
  let h = `<div class="card"><div class="lbl">기준 시나리오 결과</div><div style="margin:4px 0 8px">${gapHtml(R.gap)}</div><div class="kvs">
  <div class="kv"><span>A 매도가</span><b>${won(p.sale)}</b></div><div class="kv"><span>− 대출 상환</span><b>${won(p.aloan)}</b></div><div class="kv"><span>− 중개보수 <span class="small">(${(broRate(p.sale) * 100).toFixed(1)}% 상한)</span></span><b>${won(R.bs)}</b></div><div class="kv"><span>− 양도세</span><b>${won(p.tax)}</b></div><div class="kv"><span>= A에서 손에 쥐는 돈</span><b>${won(R.proceeds)}</b></div>
  <div class="kv"><span>B 매수가</span><b>${won(p.buy)}</b></div><div class="kv"><span>+ 취득세 등 <span class="small">(${(acqRate(p.buy, p.area) * 100).toFixed(2)}%)</span></span><b>${won(R.acq)}</b></div><div class="kv"><span>+ 중개보수</span><b>${won(R.bb)}</b></div><div class="kv"><span>+ 법무·등기 <span class="small">(0.3% 추정)</span></span><b>${won(R.legal)}</b></div><div class="kv"><span>+ 이사·수리</span><b>${won(p.move)}</b></div><div class="kv"><span>− B 대출</span><b>${won(p.bloan)}</b></div>${p.jeonse ? `<div class="kv"><span>− 전세 승계(갭)</span><b>${won(p.jeonse)}</b></div>` : ''}${p.rent ? `<div class="kv"><span>+ 내 거주 보증금</span><b>${won(p.rent)}</b></div>` : ''}<div class="kv"><span>= B에 필요한 돈</span><b>${won(R.need)}</b></div><div class="kv"><span>내 보유 현금</span><b>${won(p.cash)}</b></div></div></div>`;
  h += `<div class="card"><h3>시세가 흔들리면</h3><table class="sens"><tr><th>시나리오</th><th>A 매도</th><th>B 매수</th><th>부족(-)/여유(+)</th></tr>${sc.map((s, i) => `<tr class="${i === 1 ? 'mid' : ''}"><td>${s[0]}</td><td>${won(s[1])}</td><td>${won(s[2])}</td>${gapCell(calc(Object.assign({}, p, { sale: s[1], buy: s[2] })).gap)}</tr>`).join('')}</table><p class="note">시나리오의 시세 범위는 개별 거래 90% 범위예요.</p>
  <table class="sens" style="margin-top:12px"><tr><th>A \\ B</th>${[.95, 1, 1.05].map(k => `<th>B ${k === 1 ? '그대로' : pct(k - 1, 0)}</th>`).join('')}</tr>${[.95, 1, 1.05].map(a => `<tr class="${a === 1 ? 'mid' : ''}"><td>A ${a === 1 ? '그대로' : pct(a - 1, 0)}</td>${[.95, 1, 1.05].map(b => gapCell(calc(Object.assign({}, p, { sale: r1(p.sale * a), buy: r1(p.buy * b) })).gap)).join('')}</tr>`).join('')}</table></div>`;
  const cap = p.buy <= 150000 ? 60000 : p.buy <= 250000 ? 40000 : 20000, rg = RULES && RULES.regions[c.c.sgg] || {}, L = RULES && c.P ? loanLimit(p.buy, c.c.sgg, c.P) : null;
  h += `<div class="card"><h3>알아둘 규정 <span class="small muted">(확인 필요)</span></h3><div class="kvs"><div class="kv"><span>양도세</span><b style="font-weight:600;text-align:left;max-width:68%">${p.sale <= 120000 ? 'A 매도가가 12억 이하예요. 1세대 1주택 비과세 요건(2년 보유, 취득 당시 조정대상지역이면 2년 거주)을 채우면 0원이에요.' : 'A 매도가가 12억을 넘어요. 1세대 1주택이어도 12억 초과분에 해당하는 양도차익에는 세금이 붙어요. 세무사 확인값을 입력하세요.'}</b></div>
  <div class="kv"><span>B 대출 상한</span><b class="${p.bloan > cap ? 'up' : ''}" style="font-weight:600;text-align:left;max-width:68%">${p.bloan > cap ? `입력한 대출이 수도권 주택담보대출 상한(참고)을 넘어요. ` : ''}B ${won(p.buy)} 기준 상한 ${won(cap)} (2025-06-27 가계부채 대책 기준, 이후 변경 가능)</b></div>
  ${rg.reg !== false ? `<div class="kv"><span>일시적 2주택</span><b style="font-weight:600;text-align:left;max-width:68%">B를 먼저 사고 A를 나중에 팔면 일시적 2주택이에요. 조정대상지역은 2026-10-01부터 기존 주택 처분 기한이 3년에서 2년으로 줄었어요(경과조치 있음). 기한을 넘기면 일시적 2주택 특례를 받지 못할 수 있어요(확인 필요).</b></div>` : ''}
  ${L ? `<div class="kv"><span>소득 기준 대출 한도</span><b style="font-weight:600;text-align:left;max-width:68%">${L.noDsr ? '연소득을 입력하지 않아 DSR을 반영하지 못했어요. ' : `DSR ${won(L.dsr)} · `}LTV ${won(L.byLtv)}(${regName(c.c.sgg)}) · 상한 ${won(L.cap)} → <b>${won(L.loan)}</b>${L.noDsr ? '' : ` (${L.bind} 한도에 걸림)`}</b></div>` : ''}
  ${rg.tohu ? `<div class="kv"><span>토지거래허가구역</span><b class="${p.jeonse > 0 ? 'up' : ''}" style="font-weight:600;text-align:left;max-width:68%">B는 토허제 지역이에요. 매수 허가가 필요하고 입주 후 2년 실거주 의무가 있어 <b>전세 낀 매수(갭투자)는 사실상 어려워요</b>. 계속 무주택인 매수자에게만 임대차 종료일까지 입주를 미루는 특례가 있지만 A를 가진 갈아타기는 대부분 해당하지 않아요(확인 필요).${p.jeonse > 0 ? ' 입력한 전세 승계는 이 계산에서 쓸 수 없다고 봤어요.' : ''}</b></div>` : ''}</div></div>`;
  return h + `<div class="warn">모든 세금·수수료는 <b>추정</b>이고 <b>확인 필요</b>해요. 중개보수는 서울시·경기도 조례 요율표(두 조례의 요율·한도가 같아요) 기준이고 실제 요율은 중개사와 협의해요. 취득세는 1주택(일시적 2주택) 가정, 양도세는 입력값(비과세 가정 시 0)이에요. 대출 한도는 연소득을 입력했을 때만 LTV·상한·DSR로 계산하고 금리·만기는 가정값이에요. 실행 전 세무사·은행에 확인하세요.</div>`;
}
const FIELDS = [['sale', 'A 매도가', '추정 시세 중간값이 기본값'], ['aloan', 'A 대출 잔액', '매도 시 상환'], ['tax', 'A 양도세', '비과세 요건 충족 시 0 · 확인 필요'], ['buy', 'B 매수가', '추정 시세 중간값이 기본값'], ['bloan', 'B 대출 계획', '받을 수 있는 한도 확인 필요'], ['jeonse', 'B 전세 승계(갭)', '전세 낀 매수일 때만 · 토허제 지역은 불가'], ['cash', '보유 현금', '예금·여유자금'], ['rent', '내 거주 보증금', '갭일 때 A 매도 후 내가 살 집'], ['move', '이사·수리비', '기본 300만원']];
let PC = null;
function planInputs(xa, xb, q) {                                           // 자금 계획의 입력 기본값(홈 요약도 같은 값을 씀)
  const o = Object.assign({ aloan: 0, tax: 0, cash: 0, move: 300, jeonse: 0, rent: 0 }, st.plan);
  const num = k => { const v = q.has(k) ? +q.get(k) : o[k] != null ? +o[k] : null; return v == null ? null : Math.max(0, v || 0); };
  const p = { sale: num('sale') ?? (xa.est ? xa.est[0] : 0), buy: num('buy') ?? (xb.est ? xb.est[0] : 0), area: xb.m || 0 };
  ['aloan', 'tax', 'cash', 'move', 'jeonse', 'rent'].forEach(k => p[k] = num(k) ?? 0);
  const P = Pof(xa, q), auto = !q.has('bloan') && st.plan.bloan == null && P.income > 0 && !p.jeonse; p.bloan = auto ? loanLimit(p.buy, xb.c.sgg, P).loan : (num('bloan') ?? 0);
  return { p, P, auto };
}
function planStick(c) {                                                    // 입력 중에도 결과가 보이도록 화면 위에 고정하는 요약
  const R = calc(c.p), short = R.gap > 0;
  return `<div class="ps-l"><span class="ps-k">${short ? 'B로 갈아타려면 부족한 돈' : 'B로 갈아타고 남는 돈'}</span><b class="ps-v ${short ? 'short' : 'surplus'}">${won(Math.abs(R.gap))}</b></div><div class="ps-r">B에 필요한 돈 ${won(R.need)}<br>A 매도 후 ${won(R.proceeds)} + 현금 ${won(c.p.cash)}${c.cashSet ? '' : '<br><span class="ps-note">보유 현금 입력 전(0원 기준)</span>'}</div>`;
}
const FGROUP = { sale: 'A를 팔 때', buy: 'B를 살 때', cash: '내 자금' };
async function plan(q) {
  const { a, bs } = refs(); bar({ title: '자금 계획', sub: 'A를 팔고 B를 사려면 얼마가 필요한지 계산해요' });
  if (!a || !bs.length) return `<div class="card">홈에서 내 집(A)과 후보(B)를 먼저 고르세요.</div>`;
  const b = bs.find(x => x.id === q.get('b')) || bs[0], [xa, xb] = await Promise.all([resolve(a), resolve(b)]);
  await needRules(); const { p, P, auto } = planInputs(xa, xb, q);
  PC = { p, ea: xa.est, eb: xb.est, xa, xb, c: xb.c, P, auto, cashSet: q.has('cash') || st.plan.cash != null };
  const warn = !xa.est || !xb.est ? `<div class="warn" style="margin-bottom:12px">${!xa.est ? 'A' : 'B'}의 시세를 추정하지 못했어요. 매도가·매수가를 직접 입력하세요.</div>` : '';
  const tabs = bs.length > 1 ? `<div class="chips">${bs.map(x => `<button class="${x.id === b.id ? 'on' : ''}" data-go="#/plan?b=${x.id}">${esc(BY[x.id].name)}</button>`).join('')}</div>` : '';
  return `<div id="pstick" class="pstick">${planStick(PC)}</div><div class="cta tap" data-go="#/cmp?b=${b.id}" style="background:var(--card);color:var(--ink);padding:10px 14px"><b>A와 B 비교 보기</b><span style="font-size:20px">›</span></div><div class="ab"><div class="box"><span class="lbl">A 내 집</span><b>${esc(xa.c.name)}</b>${fa(xa.a)} · ${xa.est ? won(xa.est[0]) : '-'}</div><span class="arrow">→</span><div class="box"><span class="lbl">B 후보</span><b>${esc(xb.c.name)}</b>${fa(xb.a)} · ${xb.est ? won(xb.est[0]) : '-'}</div></div>${tabs}${warn}
  <div class="card"><h3>내 정보 <span class="small muted">(단위: 만원)</span></h3>${FIELDS.map(([k, l, hint]) => (FGROUP[k] ? `<div class="fgrp">${FGROUP[k]}</div>` : '') + `<div class="field"><label for="f-${k}">${l}<span class="hint">${k === 'bloan' && PC.auto ? '소득·규제 기준 최대치로 채움 · 직접 수정 가능' : hint}</span></label><div class="fin"><input id="f-${k}" data-k="${k}" inputmode="numeric" value="${Math.round(p[k])}"><span class="fmt" data-fm="${k}">${p[k] > 0 ? won(Math.round(p[k])) : ''}</span></div></div>`).join('')}</div><div id="res">${planResult(PC)}</div>`;
}

/* ---------- 규칙·대출·예산 계산 (조건으로 찾기와 자금 계획이 함께 씀) ---------- */
let RULES = null, CAND = null, FC = null;
const loadJson = u => fetch(dq(u)).then(r => { if (!r.ok) throw new Error('data ' + r.status); return r.json(); });
const needRules = async () => { if (!RULES) RULES = await loadJson('data/rules.json'); };
const needCand = async () => { if (!CAND) CAND = await loadJson('data/cand.json'); };
const TODAY = (location.search.match(/today=(\d{4}-\d\d-\d\d)/) || [])[1] || new Date().toISOString().slice(0, 10);
const annuity = (rate, yrs) => { const i = rate / 12, n = Math.max(1, yrs || 0) * 12; return 12 * (i ? i / (1 - Math.pow(1 + i, -n)) : 1 / n); };   // 원금 1당 연 원리금
function loanLimit(buy, sgg, P) {
  const rg = RULES.regions[sgg] || {}, byLtv = Math.floor(buy * (rg.reg === false ? RULES.ltv.other : RULES.ltv.regulated)), cap = RULES.loan_cap.find(c => c[0] == null || buy <= c[0])[1];
  const dsr = P.income > 0 ? Math.floor(Math.max(0, RULES.dsr.limit * P.income - (P.debt || 0)) / annuity(P.rate / 100 + RULES.dsr.stress, P.yrs)) : Infinity;
  const loan = Math.min(byLtv, cap, dsr), bind = isFinite(dsr) && dsr <= byLtv && dsr <= cap ? 'DSR' : cap <= byLtv ? '상한' : 'LTV';
  return { loan, byLtv, cap, dsr, bind, noDsr: !(P.income > 0) };
}
function needFor(buy, area, sgg, P, mode) {                                  // B를 buy에 살 때 내 돈이 얼마나 필요한가
  const acq = r1(buy * acqRate(buy, area)), bb = r1(broFee(buy)), legal = r1(buy * .003), base = buy + acq + bb + legal + P.move;
  if (mode === 'gap') { const jeonse = r1(buy * P.jr / 100); return { need: base - jeonse + P.rent, loan: 0, jeonse, acq, bb, legal }; }
  const L = loanLimit(buy, sgg, P); return { need: base - L.loan, loan: L.loan, L, acq, bb, legal };
}
const budgetOf = P => P.sale - P.aloan - r1(broFee(P.sale)) - P.tax + P.cash;
function maxBuy(B, area, sgg, P, mode) { let lo = 0, hi = 400000; for (let k = 0; k < 60; k++) { const m = (lo + hi) / 2; if (needFor(Math.round(m), area, sgg, P, mode).need <= B) lo = m; else hi = m; } return Math.floor(lo); }
function classify(est, area, sgg, P, mode, B) { const n = v => needFor(Math.round(v), area, sgg, P, mode).need; return n(est[2]) <= B ? '가능' : n(est[0]) <= B ? '빠듯' : '불가'; }
const PKEYS = ['sale', 'aloan', 'tax', 'cash', 'move', 'income', 'debt', 'rate', 'yrs', 'jr', 'rent'];
function Pof(xa, q) {
  const o = Object.assign({ aloan: 0, tax: 0, cash: 0, move: 300, debt: 0, rate: RULES.dsr.rate, yrs: RULES.dsr.years, jr: 60, rent: 0 }, st.plan); if (q) PKEYS.forEach(k => { if (q.has(k)) o[k] = +q.get(k); });
  const nn = v => Math.max(0, +v || 0);                                          // URL·저장값의 음수·비숫자 방어
  return { sale: nn(o.sale ?? (xa.est ? xa.est[0] : 0)), aloan: nn(o.aloan), tax: nn(o.tax), cash: nn(o.cash), move: nn(o.move), income: nn(o.income), debt: nn(o.debt), rate: nn(o.rate), yrs: nn(o.yrs), jr: nn(o.jr), rent: nn(o.rent) };
}
const regName = sgg => (RULES.regions[sgg] || {}).reg === false ? '비규제지역' : '규제지역';

/* ---------- 화면: 조건으로 후보 찾기 ---------- */
const GUN = {}, FDEF = () => ({ locs: [], mode: 'loan', range: 15, cls: { 가능: 1, 빠듯: 1, 불가: 0 }, sort: 'n12', tohu: 0 });
const SORTS = { n12: '12개월 거래 많은 순', lo: '추정 시세 낮은 순', hi: '추정 시세 높은 순', rel: '주변 대비 높은 순', dd: '하락기 낙폭 작은 순' };
const inLocs = (c, locs) => locs.includes(String(c.sgg)) || locs.includes(c.sgg + ':' + c.umd);
const gname = sgg => sgg === 41360 ? '남양주시(다산동)' : GUN[sgg] || String(sgg);
const ffield = (k, l, hint, val) => `<div class="field"><label for="x-${k}">${l}<span class="hint">${hint}</span></label><input id="x-${k}" data-fk="${k}" inputmode="decimal" value="${val ?? ''}"></div>`;
function rulesCard() {
  const age = Math.round((Date.parse(TODAY) - Date.parse(RULES.asof)) / 864e5);
  return `${age > RULES.stale_days ? `<div class="warn" style="margin-bottom:12px">규칙 기준일이 ${age}일 지났어요. 규정이 바뀌었을 수 있으니 확인하세요.</div>` : ''}<details class="card"><summary style="cursor:pointer"><b>적용한 규칙</b> <span class="small muted">(기준일 ${esc(RULES.asof)}) · 눌러서 보기</span></summary><div class="kvs" style="margin-top:8px">${RULES.items.map(i => `<div class="kv"><span style="max-width:100%;text-align:left">${esc(i.label)}<br><span class="small">${esc(i.confidence)} · <a href="${/^https?:\/\//.test(i.source) ? esc(i.source) : '#'}" target="_blank" rel="noopener">출처</a></span></span></div>`).join('')}</div><p class="note">금리·만기·전세가율은 가정값이고 직접 바꿀 수 있어요. 실제 대출·세금은 은행·세무사 확인이 필요해요.</p></details>`;
}
function fresHtml() {
  const { xa, area } = FC, F = st.find, P = Pof(xa), B = budgetOf(P), mode = F.mode;
  if (!F.locs.length) return `<div class="card tap" data-act="floc"><b>입지를 선택하세요</b><div class="note">구·동을 고르면 내 자금으로 살 수 있는 단지를 보여줘요.</div></div>`;
  const sggs = [...new Set(F.locs.map(l => +l.split(':')[0]))];
  const lines = sggs.map(g => { if (mode === 'gap' && (RULES.regions[g] || {}).tohu) return `<div class="kv"><span>${esc(gname(g))} <span class="small">${regName(g)}</span></span><b class="up">갭투자 불가<br><span class="small muted" style="font-weight:500">토허제 · 2년 실거주 의무</span></b></div>`; const m = maxBuy(B, area, g, P, mode), n = needFor(m, area, g, P, mode); return `<div class="kv"><span>${esc(gname(g))} <span class="small">${regName(g)}</span></span><b>최대 ${won(m)}<br><span class="small muted" style="font-weight:500">${mode === 'gap' ? `전세가율 ${P.jr}% 가정` : `대출 ${won(n.loan)}${n.L.noDsr ? '' : ' · ' + n.L.bind + ' 한도'}`}</span></b></div>`; }).join('');
  const rows = [];
  for (const id in CAND) { const c = BY[id]; if (!c || !inLocs(c, F.locs)) continue; const tohu = !!(RULES.regions[c.sgg] || {}).tohu; let best = null; for (const t of CAND[id]) { if (F.range && Math.abs(t[2] - area) > F.range) continue; if (!best || Math.abs(t[2] - area) < Math.abs(best[2] - area)) best = t; } if (best) rows.push({ c, a: best[0], n: best[1], m: best[2], est: [best[3], best[4], best[5]], tohu }); }   // 단지당 내 평형에 가장 가까운 하나
  const cnt = { 가능: 0, 빠듯: 0, 불가: 0, '갭 불가': 0 };
  rows.forEach(r => { r.cls = mode === 'gap' && r.tohu ? '갭 불가' : classify(r.est, r.m, r.c.sgg, P, mode, B); r.nd = needFor(r.est[0], r.m, r.c.sgg, P, mode); cnt[r.cls]++; });
  const H = FC.H, key = { n12: r => -r.c.n12, lo: r => r.est[0], hi: r => -r.est[0], rel: r => r.c.trend && r.c.trend.m === 'E' && r.c.dong ? -(r.c.trend.r - r.c.dong.med) : 9, dd: r => H && H.c[r.c.id] && H.c[r.c.id].d ? -H.c[r.c.id].d[2] : 9 }[F.sort];
  const shown = rows.filter(r => r.cls === '갭 불가' ? F.tohu : F.cls[r.cls]).sort((x, y) => key(x) - key(y) || y.c.n12 - x.c.n12), top = shown.slice(0, 40);
  const noDsr = mode === 'loan' && !(P.income > 0), allTohu = rows.length > 0 && rows.every(r => r.tohu);
  let h = `<div class="card"><div class="lbl">내 자금 기준 예산 <span class="small">(A를 팔고 남는 돈 + 보유 현금)</span></div><div class="big">${won(B)}</div><div class="kvs">${lines}</div>${allTohu && mode === 'loan' ? `<div class="note" style="margin-top:8px">선택한 입지의 단지는 모두 <b>토지거래허가구역</b>이라 매수 허가와 입주 후 2년 실거주 의무가 있어요.</div>` : ''}${noDsr ? `<div class="warn" style="margin-top:8px">연소득을 입력하지 않아 <b>DSR을 반영하지 못했어요.</b> 실제 대출 한도는 더 작을 수 있어요.</div>` : ''}</div>`;
  if (mode === 'gap') { const tg = sggs.filter(g => (RULES.regions[g] || {}).tohu); if (tg.length) h += `<div class="warn" style="margin-bottom:12px"><b>토지거래허가구역은 전세 낀 매수(갭투자)를 할 수 없다고 보고 계산해요.</b> ${esc(tg.map(gname).join(', '))}은(는) 매수 허가가 필요하고 입주 후 <b>2년 실거주 의무</b>가 있어요. 계속 무주택인 매수자에게만 임대차 종료일까지 입주를 미루는 특례가 있지만 A를 가진 갈아타기는 대부분 해당하지 않아요(확인 필요). 이 지역 단지 ${cnt['갭 불가']}개는 결과에서 뺐어요. 주담대 방식으로 바꾸면 볼 수 있어요.</div>`; }
  h += `<div class="sec"><b>살 수 있는 단지</b><span>가능 ${cnt.가능} · 빠듯 ${cnt.빠듯} · 불가 ${cnt.불가}</span></div>
  <div class="flab">내 평형(${fa(Math.round(area))})과 비슷한 범위</div><div class="chips">${[0, 10, 15, 25].map(v => `<button class="${F.range === v ? 'on' : ''}" data-act="frange:${v}">${v ? `${fa(v)} 이내` : '평형 전체'}</button>`).join('')}</div>
  <div class="flab">보여줄 결과</div><div class="chips">${['가능', '빠듯', '불가'].map(k => `<button class="${F.cls[k] ? 'on' : ''}" data-act="fcls:${k}">${k}</button>`).join('')}${mode === 'gap' ? `<button class="${F.tohu ? 'on' : ''}" data-act="ftohu">토허제 단지 보기</button>` : ''}</div>
  <div class="sortrow"><label for="fsort" class="flab" style="margin:0">정렬</label><select id="fsort" class="sel">${Object.entries(SORTS).map(([k, l]) => `<option value="${k}" ${F.sort === k ? 'selected' : ''}>${l}</option>`).join('')}</select></div>`;
  h += top.map(r => { const c = r.c, bc = r.cls === '가능' ? 'ok' : r.cls === '빠듯' ? 'flat' : 'na', why = r.cls === '가능' ? '' : r.cls === '갭 불가' ? '토지거래허가구역: 2년 실거주 의무로 갭투자 불가' : mode === 'gap' ? `필요 현금 ${won(r.nd.need)} > 예산 ${won(B)}` : `필요 자금 ${won(r.nd.need)} · 대출 ${won(r.nd.loan)}(${r.nd.L.bind} 한도)`;
    return `<div class="card tap" data-go="#/c/${c.id}?t=${r.a}"><div class="rc-top"><div><div class="rc-name">${esc(c.name)}<span class="s">${esc(c.gu)} ${esc(c.umd)} <span style="white-space:nowrap">· ${c.by}년</span></span></div></div><span class="badge ${bc}">${r.cls}</span></div>
    <div class="rc-mid"><div class="rc-r" style="text-align:left"><div class="lbl">${fa(r.a)} 추정 시세(중간층)</div><div class="big" style="font-size:21px">${won(r.est[0])}</div><div class="small muted">${won(r.est[1])} ~ ${won(r.est[2])}</div></div><div style="text-align:right">${badge(c.trend)}${c.trend ? `<div class="small muted" style="margin-top:4px">${pct(c.trend.r)} ${c.trend.m === 'E' ? '최근 6개월' : '평균'}</div>` : ''}</div></div>
    ${why ? `<div class="rel">${esc(why)}</div>` : ''}<div class="rc-foot">${r.tohu && !allTohu ? '<span class="chip reg">토허제</span>' : ''}<span>12개월 거래 ${c.n12}건</span>${c.dong && c.trend && c.trend.m === 'E' ? `<span>· 주변 대비 ${(c.trend.r - c.dong.med) * 100 >= 0 ? '+' : ''}${((c.trend.r - c.dong.med) * 100).toFixed(1)}%p</span>` : ''}</div>
    ${r.cls === '갭 불가' ? '' : `<div class="row" style="margin-top:8px"><button class="chip tap" data-act="fadd:${c.id}:${r.a}" style="padding:7px 14px;font-size:13px">후보에 추가</button><button class="chip tap" data-act="fplan:${c.id}:${r.a}" style="padding:7px 14px;font-size:13px">자금 계획 ›</button></div>`}</div>`; }).join('');
  if (!top.length) h += `<div class="card">조건에 맞는 단지가 없어요. 입지나 평형 범위를 넓히거나, '불가'·'빠듯'도 함께 보세요.</div>`;
  else if (shown.length > top.length) h += `<p class="note">${shown.length}개 중 ${top.length}개를 보여줘요. 입지를 동 단위로 좁히거나 평형 범위를 줄여 보세요.</p>`;
  return h + `<p class="note">시세는 평형·층을 보정한 추정치(중간층)이고 90% 범위로 가능·빠듯·불가를 나눠요(범위 전체가 예산 안이면 가능, 중간값만 안이면 빠듯). 조건에 맞는 단지를 모아 보여주는 목록이고 투자 권유가 아니에요.</p>`;
}
async function find(q) {
  await Promise.all([needRules(), needCand()]); const HH = await hist();
  const { a } = refs(); bar({ title: '조건으로 후보 찾기', back: true, sub: '입지를 고르면 내 자금으로 살 수 있는 단지를 보여줘요' });
  IDX.c.forEach(c => { GUN[c.sgg] = c.gu; });
  if (!a) return `<div class="card tap" data-act="pick-a"><b>내 집(A)을 먼저 선택하세요</b></div>`;
  const xa = await resolve(a), F = st.find = Object.assign(FDEF(), st.find || {});
  if (q.has('loc')) F.locs = q.get('loc').split(',').filter(Boolean); if (q.has('mode')) F.mode = q.get('mode'); if (q.has('range')) F.range = +q.get('range'); if (q.has('sort')) F.sort = q.get('sort'); if (q.has('tohu')) F.tohu = +q.get('tohu');
  if (q.has('cls')) F.cls = Object.fromEntries(['가능', '빠듯', '불가'].map(k => [k, q.get('cls').split(',').includes(k) ? 1 : 0]));
  PKEYS.forEach(k => { if (q.has(k)) st.plan[k] = +q.get(k); });
  const P = Pof(xa), o = st.plan; FC = { xa, area: xa.m || 84, H: HH };
  const locTxt = F.locs.length ? F.locs.map(l => { const [g, u] = l.split(':'); return esc(u ? `${gname(+g)} ${u}` : gname(+g)); }).join(', ') : '아직 선택하지 않았어요';
  return `<div class="card"><div class="row"><b>입지</b><button class="chip tap" data-act="floc" style="padding:7px 14px;font-size:13px">${F.locs.length ? '변경' : '선택'} ›</button></div><div class="note" id="locsum" style="margin-top:6px">${locTxt}</div></div>
  <div class="card"><h3>살 방법</h3><div class="theme"><button class="${F.mode === 'loan' ? 'on' : ''}" data-act="fmode:loan">주담대</button><button class="${F.mode === 'gap' ? 'on' : ''}" data-act="fmode:gap">갭(전세 낀 매수)</button></div></div>
  <details class="card" ${o.income > 0 ? '' : 'open'}><summary style="cursor:pointer"><b>내 자금</b> <span class="small muted">(단위: 만원) · ${o.income > 0 ? `연소득 ${won(o.income)} · 현금 ${won(P.cash)} · 눌러서 수정` : '연소득을 입력하세요'}</span></summary>${ffield('cash', '보유 현금', '예금·여유자금', P.cash)}${ffield('income', '가구 연소득(세전)', '가구 전체 합산 · DSR 계산에 사용', o.income ?? '')}<details class="adv"><summary class="advsum">더 정확하게 계산하려면 <span class="small muted">(A 매도가·대출·세금·금리)</span></summary>${ffield('sale', 'A 매도가', '추정 시세 중간값이 기본값', Math.round(P.sale))}${ffield('aloan', 'A 대출 잔액', '매도 시 상환', P.aloan)}${ffield('tax', 'A 양도세', '비과세 요건 충족 시 0 · 확인 필요', P.tax)}${ffield('debt', '기타 대출 연 원리금', '다른 대출이 있으면 1년 상환액', P.debt)}${ffield('move', '이사·수리비', '기본 300만원', P.move)}
  ${F.mode === 'loan' ? ffield('rate', '대출 금리(연 %)', '가정값 · 스트레스 금리 3.0%p는 별도 가산', P.rate) + ffield('yrs', '대출 만기(년)', '가정값', P.yrs) : ffield('jr', '전세가율(%)', '가정값 · 매매가 대비 전세 승계금', P.jr) + ffield('rent', '내 거주 보증금', 'A 매도 후 내가 살 집의 보증금', P.rent)}</details></details>
  <div id="fres">${fresHtml()}</div>${rulesCard()}`;
}
function locSheet() {
  const row = g => { const on = st.find.locs.includes(String(g)), dn = st.find.locs.filter(l => l.startsWith(g + ':')).length, tohu = (RULES.regions[g] || {}).tohu;
    return `<div class="locrow"><button class="pick" data-act="loc:${g}"><span>${esc(gname(g))}${tohu ? ' <span class="chip reg">토허제</span>' : ''}${dn ? ` <span class="chip">동 ${dn}곳</span>` : ''}</span><span>${on ? '✓' : ''}</span></button><button class="chip tap" data-act="dong:${g}">동 ›</button></div>`; };
  const sg = Object.keys(RULES.regions).map(Number); sheet('입지 선택', `<div class="grp">서울</div>${sg.filter(g => g < 20000).map(row).join('')}<div class="grp">경기</div>${sg.filter(g => g > 40000).map(row).join('')}<button class="cta" data-act="fdone" style="width:100%;margin-top:10px"><b>선택 완료</b></button>`);
}
function dongSheet(g) {
  const us = [...new Set(IDX.c.filter(c => c.sgg === +g && CAND[c.id]).map(c => c.umd))].sort(), L = st.find.locs;
  sheet(`${gname(+g)} 동 선택`, `<div class="chips"><button class="${L.includes(String(g)) ? 'on' : ''}" data-act="loc:${g}:back">구 전체</button>${us.map(u => `<button class="${L.includes(g + ':' + u) ? 'on' : ''}" data-act="dloc:${g}:${u}">${esc(u)}</button>`).join('')}</div><button class="cta" data-act="floc" style="width:100%;margin-top:10px"><b>← 구 목록으로</b></button>`);
}
function addB(id, type) { st.bs = (st.bs || []).filter(b => !b.sample && b.id !== id); if (st.bs.length >= 5) st.bs.shift(); st.bs.push({ id, type: +type, tier: 1 }); save(); }

/* ---------- 화면: 관심 입지(동·구 단위 가격 추이와 환금성) ---------- */
let AP = null, AREA = null;
const areaData = () => AP || (AP = fetch(dq('data/area.json')).then(r => { if (!r.ok) { AP = null; throw new Error('data ' + r.status); } return r.json(); }));
const ACOL = ['var(--ln)', 'var(--accent)', '#7A5AC8', '#2BA68C', '#8A93B2'];
const aname = (k, a) => k.includes(':') ? (a.sgg === 41360 ? '남양주시 ' : gname(a.sgg) + ' ') + a.name : gname(a.sgg);
const rebase = (p, s) => p.map(v => v == null || p[s] == null ? null : v / p[s] * 100);
const roll4 = c => c.map((_, i) => i >= 3 && i < c.length - 1 ? c[i] + c[i - 1] + c[i - 2] + c[i - 3] : null);   // 4분기 합. 마지막 분기는 신고가 덜 들어와 제외
const volIdx = a => { const r = roll4(a.cnt), v = r.filter(x => x != null), m = v.length ? v.reduce((x, y) => x + y, 0) / v.length : 0; return r.map(x => x == null || !m ? null : x / m * 100); };
const sgn = v => v == null ? '' : v >= 0 ? 'up' : 'down';
const atog = key => { const L = st.areas; const i = L.indexOf(key); if (i >= 0) L.splice(i, 1); else { L.push(key); if (L.length > 5) L.shift(); } save(); };
function areaCard(k, a, AD, i) {
  const th = a.idx == null, lvl = k.includes(':') ? '동' : '구·시', rk = (r, w) => r ? ` <span class="small muted">· ${w} ${r[1]}곳 중 ${r[0]}위 (상위 ${Math.max(1, Math.round(r[0] / r[1] * 100))}%)</span>` : '';
  const yoy = a.t12p ? a.t12 / a.t12p - 1 : null, vs = a.avg10 ? a.t12 / a.avg10 - 1 : null, kv = (l, v) => `<div class="kv"><span>${l}</span><b>${v}</b></div>`;
  let h = `<div class="card"><div class="row"><h3 style="margin:0"><span style="color:${ACOL[i]}">●</span> ${esc(aname(k, a))} <span class="small muted">${lvl} · 단지 ${a.nc}개</span></h3><button class="chip tap" data-act="${k.includes(':') ? 'atd:' + k : 'at:' + k}">빼기</button></div>`;
  h += `<div class="lbl" style="margin-top:10px">가격 추이</div>`;
  if (th) h += `<div class="rel muted">가격 흐름을 만들 만큼 거래가 쌓인 단지가 ${a.ni}개뿐이라(분기마다 ${AD.meta.min_c}개 필요) 이 ${lvl}의 가격 추이는 내지 않았어요. 상위 구·시로 보세요.</div>${k.includes(':') ? `<button class="chip tap" data-act="at:${a.sgg}" style="margin-top:8px;padding:7px 14px;font-size:13px">${esc(gname(a.sgg))} 보기</button>` : ''}`;
  else {
    const [c6, c12, fp] = a.ch, dd = a.dd;
    h += `<div class="kvs">${a.px84 ? kv(fa(84) + ' 환산 시세 <span class="small muted">(참고)</span>', won(a.px84)) : ''}${kv('6개월 변화', c6 == null ? '-' : `<span class="${sgn(c6)}">${pct(c6)}</span>`)}${kv('12개월 변화', c12 == null ? '-' : `<span class="${sgn(c12)}">${pct(c12)}</span>${rk(a.rk12, lvl)}`)}${kv('최고 분기 대비', fp >= 0 ? '최근 분기가 10년 중 최고' : pct(fp))}`;
    h += dd == null ? kv('2022~23 하락기', '이 구간 지수가 모자라 계산하지 못했어요') : dd[2] === 0 ? kv('2022~23 하락기', `고점(${dd[0]}) 이후 더 낮아진 분기가 없었어요`) : kv('하락기 낙폭', `<span class="down">${pct(dd[2])}</span>`) + kv('고점 → 저점', `${dd[0]} → ${dd[1]}<span class="small muted">${dd[3] != null ? ` · ${dd[3]}분기 만에 회복` : fp > -0.02 ? ' · 최근 지수는 고점 수준' : ' · 아직 회복 전'}</span>`);
    h += `</div>`;
  }
  h += `<div class="lbl" style="margin-top:12px">환금성</div><div class="kvs">${kv('최근 12개월 거래', `${a.t12.toLocaleString('ko-KR')}건${yoy == null ? '' : ` <span class="small muted">· 전년 대비</span> <span class="${sgn(yoy)}">${pct(yoy)}</span>`}`)}${kv('10년 평균 대비', vs == null ? '-' : `<span class="${sgn(vs)}">${pct(vs)}</span> <span class="small muted">· 연평균 ${Math.round(a.avg10).toLocaleString('ko-KR')}건</span>`)}${kv('단지당 12개월 거래', `${a.per12}건${rk(a.rkliq, lvl)}`)}${kv('최근 12개월 거래가 있던 단지', `${a.act}/${a.nc}개`)}${kv('최근 3개월 거래', `${a.t3}건`)}${kv('하락기 거래량 변화', a.vd ? `<span class="down">${pct(a.vd[2])}</span> <span class="small muted">· 고점 ${a.vd[0]} → 저점 ${a.vd[1]}</span>` : '-')}</div>`;
  return h + `<button class="chip tap" data-go="#/find?loc=${esc(k)}" style="margin-top:10px;padding:7px 14px;font-size:13px">이 입지에서 살 수 있는 단지 찾기</button></div>`;
}
async function area(q) {
  const AD = AREA = await areaData(); refs(); IDX.c.forEach(c => { GUN[c.sgg] = c.gu; }); bar({ title: '관심 입지', sub: '동·구 단위 가격 추이와 환금성' });
  if (q.has('loc')) st.areas = q.get('loc').split(',').filter(k => AD.a[k]).slice(0, 5);
  if (!st.areas) { const A = st.a && BY[st.a.id]; st.areas = A && AD.a[`${A.sgg}:${A.umd}`] ? [`${A.sgg}:${A.umd}`] : []; }
  const ks = st.areas.filter(k => AD.a[k]), m = AD.meta; st.areas = ks;
  const pick = `<button class="cta" data-act="aloc" style="width:100%;margin-bottom:12px"><b>관심 입지 ${ks.length ? '추가·변경' : '고르기'}</b> <span class="small">(최대 5곳, 동 또는 구·시)</span></button>`;
  if (!ks.length) return `${pick}<div class="card">관심 있는 동이나 구·시를 고르면 그 입지의 가격 추이와 거래가 얼마나 활발한지를 보여줘요.</div>`;
  const legend = `<div class="legend">${ks.map((k, i) => `<span><i style="border-top-color:${ACOL[i]};border-top-style:solid"></i>${esc(aname(k, AD.a[k]))}</span>`).join('')}</div>`;
  const wi = ks.filter(k => AD.a[k].idx), s = wi.length ? Math.max(...wi.map(k => AD.a[k].idx.findIndex(v => v != null))) : -1;
  const pl = wi.filter(k => AD.a[k].idx[s] != null).map(k => ({ p: rebase(AD.a[k].idx, s), c: ACOL[ks.indexOf(k)] }));
  let h = pick;
  h += `<div class="card"><h3>가격 추이 <span class="small muted">(${pl.length ? qlab(m, s) + ' = 100' : ''})</span></h3>${pl.length ? multiChart(m, pl, v => v.toFixed(0), 'chartA1') : '<div class="rel muted">선택한 입지에는 가격 추이를 낼 만큼 거래가 쌓인 곳이 없어요.</div>'}${legend}</div>`;
  const vl = ks.map((k, i) => ({ p: volIdx(AD.a[k]), c: ACOL[i] })).filter(l => l.p.some(v => v != null));
  h += `<div class="card"><h3>거래량 추이 <span class="small muted">(4분기 합, 10년 평균 = 100)</span></h3>${vl.length ? multiChart(m, vl, v => v.toFixed(0), 'chartA2') : ''}${legend}<p class="note">100보다 높으면 그 입지의 10년 평균보다 거래가 활발했다는 뜻이에요. 거래가 많을수록 팔고 싶을 때 거래가 이어졌던 곳이에요.</p></div>`;
  if (ks.length >= 2) { const sn = k => k.includes(':') ? AD.a[k].name : gname(AD.a[k].sgg), yo = a => a.t12p ? a.t12 / a.t12p - 1 : null, cell = (v, f) => v == null ? '-' : f(v), c1 = a => a.ch && a.ch[1], dd = a => a.dd && a.dd[2] < 0 ? a.dd[2] : a.dd ? 0 : null;
    const row = (l, f) => `<tr><td>${l}</td>${ks.map(k => `<td>${f(AD.a[k])}</td>`).join('')}</tr>`;
    h += `<div class="card"><h3>한눈에 비교</h3><table class="tbl cmpt"><tr><th></th>${ks.map((k, i) => `<th><span style="color:${ACOL[i]}">●</span> ${esc(sn(k))}</th>`).join('')}</tr>${row('12개월 변화', a => cell(c1(a), v => `<span class="${sgn(v)}">${pct(v)}</span>`))}${row('하락기 낙폭', a => cell(dd(a), v => v === 0 ? '없음' : `<span class="down">${pct(v)}</span>`))}${row('12개월 거래', a => `${a.t12.toLocaleString('ko-KR')}건`)}${row('전년 대비', a => cell(yo(a), v => `<span class="${sgn(v)}">${pct(v)}</span>`))}${row('단지당 거래', a => `${a.per12}건`)}</table></div>`; }
  h += ks.map((k, i) => areaCard(k, AD.a[k], AD, i)).join('');
  h += `<p class="note">가격 추이는 입지 안 단지들의 분기 가격에서 단지별 가격 수준 차이를 빼고 합친 지수예요(분기마다 단지 ${m.min_c}개 이상일 때만). 거래량은 10년간 거래 12건 이상인 단지만 세고, 최근 분기는 신고가 덜 들어와 뺐어요. 취소·직거래는 2021-11 이전에는 구분하지 못했어요. 세대수는 반영하지 않아 단지당 거래는 큰 단지가 많은 곳에서 높게 나와요. 과거 기록이며 같은 흐름이 반복된다는 뜻은 아니에요. 데이터 기준 ${esc(m.end)}.</p>`;
  return h;
}
let AQ = '';                                                                  // 관심 입지 검색어
const asel = k => k.includes(':') ? 'atd:' + k : 'at:' + k;
function areaList() {
  const AD = AREA, q = AQ.trim().toLowerCase().split(/\s+/).filter(Boolean), selected = st.areas.length ? `<div class="chips" style="margin-bottom:8px">${st.areas.filter(k => AD.a[k]).map(k => `<button class="on" data-act="${asel(k)}">${esc(aname(k, AD.a[k]))} ✕</button>`).join('')}</div>` : '';
  const row = g => { const on = st.areas.includes(String(g)), dn = st.areas.filter(l => l.startsWith(g + ':')).length;
    return `<div class="locrow"><button class="pick" data-act="at:${g}"><span>${esc(gname(g))}${dn ? ` <span class="chip">동 ${dn}곳</span>` : ''}</span><span>${on ? '✓' : ''}</span></button><button class="chip tap" data-act="adong:${g}">동 ›</button></div>`; };
  let h;
  if (!q.length) { const sg = Object.keys(AD.a).filter(k => !k.includes(':')).map(Number).sort((x, y) => x - y); h = `<div class="grp">서울</div>${sg.filter(g => g < 20000).map(row).join('')}<div class="grp">경기</div>${sg.filter(g => g > 40000).map(row).join('')}`; }
  else {
    const hit = Object.keys(AD.a).filter(k => { const nm = norm(aname(k, AD.a[k])); return q.every(t => nm.includes(t)); }).sort((x, y) => (x.includes(':') - y.includes(':')) || aname(x, AD.a[x]).localeCompare(aname(y, AD.a[y]), 'ko'));
    const r = k => { const a = AD.a[k], on = st.areas.includes(k), dong = k.includes(':'); return `<div class="locrow"><button class="pick" data-act="${asel(k)}"><span>${esc(aname(k, a))} <span class="chip">${dong ? '동' : '구·시'}</span>${a.idx ? '' : ' <span class="small muted">추이 없음</span>'}</span><span>${on ? '✓' : ''}</span></button></div>`; };
    h = hit.length ? hit.slice(0, 40).map(r).join('') + (hit.length > 40 ? `<div class="note">${hit.length - 40}곳이 더 있어요. 더 입력해 좁혀 보세요.</div>` : '') : `<div class="note">"${esc(AQ.trim())}"에 맞는 입지가 없어요. 동 이름(예: 정자동)이나 구·시 이름(예: 분당, 노원)으로 찾아보세요.</div>`;
  }
  $('#al').innerHTML = selected + h;
}
function areaSheet() {
  sheet('관심 입지 선택 (최대 5곳)', `<input class="search" id="aq" placeholder="동·구 이름 검색 (예: 분당, 정자동, 월계)" autocomplete="off" value="${esc(AQ)}"><div id="al"></div><button class="cta" data-act="adone" style="width:100%;margin-top:10px"><b>선택 완료</b></button>`); areaList();
}
function areaDongSheet(g) {
  const AD = AREA, us = Object.keys(AD.a).filter(k => k.startsWith(g + ':')).sort((x, y) => x.localeCompare(y, 'ko'));
  sheet(`${gname(+g)} 동 선택`, `<div class="chips"><button class="${st.areas.includes(String(g)) ? 'on' : ''}" data-act="at:${g}:back">구·시 전체</button>${us.map(k => `<button class="${st.areas.includes(k) ? 'on' : ''}" data-act="atd:${k}">${esc(AD.a[k].name)}${AD.a[k].idx ? '' : ' (추이 없음)'}</button>`).join('')}</div><button class="cta" data-act="aloc" style="width:100%;margin-top:10px"><b>← 구·시 목록으로</b></button>`);
}

/* ---------- 사용 가이드(온보딩) ---------- */
const tl = (n, t, d) => `<div class="tl"><i>${n}</i><div><b>${t}</b><div class="small muted">${d}</div></div></div>`;
const tlink = (n, t, d, href) => `<button class="tl tl-link" data-go="${href}"><i>${n}</i><div><b>${t}</b><div class="small muted">${d}</div></div><span class="chev" aria-hidden="true">›</span></button>`;   // 줄 전체를 눌러 이동
function tourSteps() {
  const b0 = (refs().bs || [])[0], bid = b0 ? b0.id : '';
  const go = (href, l) => `<button class="chip tap act-main" data-go="${href}" style="margin-top:6px">${l} ›</button>`;
  return [
    { h: '갈아탈 때 필요한 걸 한곳에서 봐요', b: `${tl(1, '두 단지의 가격 흐름', '내 집(A)과 후보(B)의 최근 실거래로 6개월 추세와 10년 흐름을 비교해요.')}${tl(2, '필요한 돈', 'A를 팔고 B를 사려면 얼마가 부족하거나 남는지 세금·수수료까지 계산해요.')}${tl(3, '관심 입지', '동·구 단위 가격 추이와 거래가 얼마나 활발한지 확인해요.')}<p class="note">모든 숫자는 실거래로 계산한 <b>추정</b>이에요. 투자 권유가 아니고, 입력한 정보는 이 기기에만 저장돼요.</p>` },
    { h: '먼저 내 집(A)과 후보(B)를 정해요', b: `<div class="ab"><div class="box"><span class="lbl">A 내 집</span><b>내가 사는 단지</b>평형·층 선택</div><span class="arrow">→</span><div class="box"><span class="lbl">B 후보</span><b>옮겨 갈 단지</b>최대 5개</div></div><p class="note" style="margin-top:0">지금은 예시 단지로 채워져 있어요. 내 집을 고르면 추세와 자금 계획이 내 상황에 맞게 바뀌어요. 후보는 홈의 <b>+</b> 버튼이나 <b>조건으로 후보 찾기</b>에서 추가해요.</p><button class="chip tap act-main" data-act="pick-a" style="margin-top:4px">내 집 고르기 ›</button>` },
    { h: '숫자는 이렇게 읽어요', b: `<div class="tour-demo">${badge({ m: 'E', s: '상승', sure: true })}<span class="hero-pct up" style="font-size:26px">+19.4%<span class="small muted" style="font-weight:500"> 최근 6개월</span></span></div><div class="small muted" style="margin:2px 0 10px">90% 범위 +15.1% ~ +23.8%</div>${tl('%', '최근 6개월 변화', '같은 단지·같은 조건으로 본 가격이 6개월 동안 얼마나 변했는지예요.')}${tl('~', '90% 범위', '실제 값이 이 안에 들어올 가능성이 90%인 구간이에요. 넓을수록 불확실해요.')}<div class="tour-badges"><div>${badge({ m: 'E', s: '상승', sure: true })}<span class="small muted">범위 전체가 같은 방향이에요</span></div><div>${badge({ m: 'E', s: '주춤', sure: false })}<span class="small muted">±3% 기준에 걸쳐 단정하기 어려워요</span></div><div>${badge({ m: 'A' })}<span class="small muted">거래가 적어 평균만 보여줘요</span></div></div>` },
    { h: '후보와 입지를 둘러봐요', b: `<p class="note" style="margin-top:0">눌러서 바로 열어 볼 수 있어요.</p>${tlink(1, '조건으로 후보 찾기', '연소득·보유 현금을 넣으면 살 수 있는 단지를 가능·빠듯·불가로 나눠 보여줘요.', '#/find')}${tlink(2, '관심 입지', '동·구를 최대 5곳 골라 가격 추이와 환금성을 비교해요. 이름으로 검색할 수 있어요.', '#/area')}${bid ? tlink(3, 'A와 B 비교', '두 단지를 표와 10년 상대 흐름으로 나란히 봐요.', '#/cmp?b=' + bid) : ''}` },
    { h: '마지막으로 필요한 돈을 확인해요', b: `<p class="note" style="margin-top:0">자금 계획에서 A를 팔고 B를 사려면 얼마가 부족하거나 남는지 볼 수 있어요. 아래를 넣으면 더 정확해져요.</p><div class="tour-check"><span>✓ 보유 현금</span><span>✓ A 대출 잔액</span><span>✓ 가구 연소득 <small class="muted">(대출 한도 계산)</small></span></div>${tl('㎡', '면적 단위', '화면 위 오른쪽 ㎡ | 평 버튼으로 바꿀 수 있어요.')}${tl('?', '용어가 어려우면', '설정의 용어 설명을 보세요. 이 가이드도 설정에서 다시 볼 수 있어요.')}${bid ? go('#/plan?b=' + bid, '자금 계획 열기') : ''}` },
  ];
}
function tourStep(i) {
  const T = tourSteps(), n = T.length; i = Math.max(0, Math.min(n - 1, i));
  sheet(`사용 가이드 ${i + 1}/${n}`, `<div class="tour"><div class="tour-top"><div class="tour-dots" aria-hidden="true">${T.map((_, k) => `<i class="${k === i ? 'on' : ''}"></i>`).join('')}</div><button class="tour-skip" data-act="tour:end">건너뛰기</button></div><h3 class="tour-h">${T[i].h}</h3>${T[i].b}<div class="tour-nav">${i ? `<button class="chip tap" data-act="tour:${i - 1}">이전</button>` : '<span></span>'}<button class="cta tour-next" data-act="tour:${i < n - 1 ? i + 1 : 'end'}"><b>${i < n - 1 ? '다음' : '시작하기'}</b></button></div></div>`);
  const sh = $('#sheet'); sh.setAttribute('role', 'dialog'); sh.setAttribute('aria-modal', 'true'); sh.setAttribute('aria-label', '사용 가이드'); sh.tabIndex = -1; sh.focus();
}

/* ---------- 화면: 설정 ---------- */
async function settings() {
  bar({ title: '설정' }); const m = IDX.meta;
  const GLOSS = [['6개월 추세', '같은 단지 안에서 층·평형 차이를 보정해 본 최근 6개월 가격 변화율이에요.'], ['상승·주춤·하락', '6개월 변화가 +3% 이상이면 상승, -3% 이하면 하락, 그 사이는 주춤이에요.'], ['확실·추정', '90% 범위 전체가 기준(±3%)을 넘으면 확실, 걸쳐 있으면 추정이에요.'], ['참고용', '최근 거래가 적어 상승·하락을 가르지 않고 평균만 보여주는 표시예요.'], ['90% 범위', '실제 값이 이 구간에 들어올 가능성이 90%라는 뜻이에요.'], ['중간값', '크기순으로 세웠을 때 가운데 값이에요. 극단값에 덜 흔들려요.'], ['가능·빠듯·불가', '시세 범위의 높은 쪽까지 내 자금으로 감당되면 가능, 중간값까지만 되면 빠듯, 중간값도 안 되면 불가예요.'], ['환금성', '최근 거래가 얼마나 자주 이뤄졌는지예요. 많을수록 팔고 싶을 때 거래가 이어졌던 곳이에요.'], ['평(전용)', '전용면적을 1평 = 3.3058㎡로 환산한 값이에요. 공급면적 기준 평형과 달라요.']];
  const tg = `<div class="card"><h3>사용 가이드</h3><button class="act" data-act="tour:0">사용 가이드 다시 보기 ›</button><p class="note">내 집과 후보 고르기, 숫자 읽는 법, 후보·입지 둘러보기, 필요한 돈 확인까지 5단계로 안내해요.</p></div>`;
  const gl = `<div class="card"><h3>용어 설명</h3>${GLOSS.map(([t, d]) => `<div class="gl"><b>${t}</b><span>${d}</span></div>`).join('')}</div>`;
  return `<div class="card"><h3>면적 단위</h3><div class="theme">${[['m2', '㎡ (전용면적)'], ['py', '평 (전용 환산)']].map(([k, l]) => `<button class="${unitOf() === k ? 'on' : ''}" data-act="unit:${k}">${l}</button>`).join('')}</div><p class="note">평은 전용면적을 1평 = 3.3058㎡로 환산한 값이에요. 분양·공급면적 기준 평형(예: 84㎡ ≈ 34평형)과는 달라요.</p></div>
  <div class="card"><h3>화면 테마</h3><div class="theme">${[['auto', '자동'], ['light', '라이트'], ['dark', '다크']].map(([k, l]) => `<button class="${st.theme === k ? 'on' : ''}" data-act="theme:${k}">${l}</button>`).join('')}</div></div>
  ${tg}${gl}
  <div class="card"><h3>데이터 기준</h3><div class="kvs"><div class="kv"><span>추세 기준일</span><b>${esc(m.end)}</b></div><div class="kv"><span>수집 기간</span><b>${dateOf(m.first_day).slice(0, 7)} ~ ${dateOf(m.last_day).slice(0, 7)}</b></div><div class="kv"><span>수집 마지막 거래일</span><b>${dateOf(m.last_day)}</b></div><div class="kv"><span>수록 단지</span><b>${m.n.toLocaleString('ko-KR')}개</b></div></div><p class="note">서울 25개 구, 구리, 하남, 남양주 다산동, 수원(장안·권선·팔달·영통), 성남 분당, 안양 동안, 의왕, 화성 동탄의 아파트 중 거래 12건 이상 단지만 담았어요. 이 밖의 수도권 지역은 아직 없어요. 출처: 국토교통부 아파트 매매 실거래가. 신고 지연을 감안해 기준일은 두 달 전 월말이에요.</p></div>
  <div class="card"><button class="act danger" data-act="reset" style="border:0;padding:6px 0">내 정보 초기화</button><p class="note">저장된 A·B 단지와 자금 입력값을 이 기기에서 지워요. 서버로 보내는 정보는 없어요.</p></div>`;
}

/* ---------- 렌더 ---------- */
let seq = 0;
async function render(keep) {
  const my = ++seq, r = parse(); setTabs(r.name === 'c' || r.name === 'cmp' ? 'home' : r.name); $('#fab').style.display = r.name === 'home' ? '' : 'none';
  const lt = keep === true ? 0 : setTimeout(() => { if (my === seq) $('#view').innerHTML = '<div class="card muted" role="status">불러오는 중…</div>'; }, 350);   // 오래 걸릴 때만 안내
  try {
    const h = r.name === 'c' ? await detail(r.arg, r.q) : r.name === 'plan' ? await plan(r.q) : r.name === 'cmp' ? await compare(r.q) : r.name === 'find' ? await find(r.q) : r.name === 'area' ? await area(r.q) : r.name === 'settings' ? await settings() : await home();
    if (my !== seq) return; const sc = $('#view').scrollTop; $('#view').innerHTML = h; a11y($('#view')); $('#view').scrollTop = keep === true ? sc : 0; save();
    if (/sheet=pick-a/.test(location.hash)) picker('a'); else if (/sheet=pick-b/.test(location.hash)) picker('b');
  } catch (e) { fail(e); } finally { clearTimeout(lt); }
}
function fail(e) { const msg = String((e && e.message) || e); $('#view').innerHTML = `<div class="card">${/^data |Failed to fetch|JSON/.test(msg) ? '데이터를 불러오지 못했습니다. 로컬 서버(127.0.0.1)로 열어 주세요.' : '화면을 그리는 중 오류가 났습니다.'}<div class="small muted" style="margin-top:6px">${esc(msg)}</div></div>`; const pre = document.createElement('pre'); pre.id = 'err'; pre.textContent = 'JS 오류: ' + msg; document.body.appendChild(pre); }

/* ---------- 단지 선택 ---------- */
let PEND = null;
const norm = s => s.replace(/\s+/g, '').toLowerCase();
function picker(role) {
  const lst = q => { const k = norm(q); const l = (k ? IDX.c.filter(c => norm(c.name + c.gu + c.umd).includes(k)) : IDX.c.filter(c => c.n12 >= 20)).sort((a, b) => b.n12 - a.n12).slice(0, 40); return l.map(c => `<button class="pick" data-pick="${role}:${c.id}"><span><b>${esc(c.name)}</b><br><span class="small muted">${esc(c.gu)} ${esc(c.umd)} · ${c.by}년 · 12개월 ${c.n12}건</span></span>${badge(c.trend)}</button>`).join('') || '<p class="muted">검색 결과가 없습니다.</p>'; };
  sheet(role === 'a' ? '내 집(A) 선택' : '후보(B) 추가', `<input class="search" id="q" placeholder="단지명·구·동 검색 (예: 래미안, 강남, 다산동)" autocomplete="off"><div id="pl">${lst('')}</div>`);
  $('#q').addEventListener('input', e => { $('#pl').innerHTML = lst(e.target.value.trim()); });
}
async function step2(role, id, pre) {
  const d = await det(id), c = BY[id]; PEND = { role, id, type: pre && pre.type != null ? pre.type : d.types.length ? typeOf({ role }, d) : null, floor: pre && pre.floor || 9, tier: pre && pre.tier != null ? pre.tier : 1, edit: !!pre };
  if (!d.types.length) return sheet(c.name, '<p class="note">최근 12개월 거래가 적어 시세를 추정할 수 없는 단지예요. 다른 단지를 골라 주세요.</p>');
  sheet(c.name, `<div class="lbl">전용면적</div><div class="chips" id="ty">${d.types.map(t => `<button data-ty="${t.a}" class="${t.a === PEND.type ? 'on' : ''}">${fa(t.a)} · ${t.n}건</button>`).join('')}</div>` +
    (role === 'a' ? `<div class="lbl">내 층</div><input class="fld" id="fl" inputmode="numeric" value="${PEND.floor}" aria-label="층">` : d.tiers ? `<div class="lbl">층대</div><div class="chips" id="tr">${TIER.map((l, i) => `<button data-tr="${i}" class="${i === PEND.tier ? 'on' : ''}">${l}</button>`).join('')}</div>` : '') + `<button class="cta" data-act="commit" style="width:100%;margin-top:10px"><b>${PEND.edit ? '변경 저장' : role === 'a' ? '내 집으로 설정' : '후보에 추가'}</b></button>`);
}
async function editSheet(role, id) {                                       // 저장된 A/B의 평형·층(대)만 바꾸기
  const d = await det(id), cur = role === 'a' ? st.a : (st.bs || []).find(b => b.id === id); if (!cur) return;
  step2(role, id, { type: typeOf({ role, type: cur.type }, d), floor: cur.floor, tier: cur.tier ?? 1 }).catch(fail);
}
function commit() {
  const P = PEND; if (!P) return;
  if (P.role === 'a') st.a = Object.assign({ id: P.id, type: P.type, floor: Math.max(1, +($('#fl') || {}).value || 9) }, st.a && st.a.id === P.id ? { buy: st.a.buy, ym: st.a.ym } : {});   // 같은 단지면 취득가·취득월 유지
  else if (P.edit) st.bs = st.bs.map(b => b.id === P.id ? { id: P.id, type: P.type, tier: P.tier } : b);
  else { st.bs = (st.bs || []).filter(b => !b.sample && b.id !== P.id); if (st.bs.length >= 5) st.bs.shift(); st.bs.push({ id: P.id, type: P.type, tier: P.tier }); }
  PEND = null; save(); closeSheet(); nav('#/home'); render();
}

/* ---------- 이벤트 ---------- */
function act(a) {
  const [k, v, w] = a.split(':');
  if (k === 'back') { history.length > 1 ? history.back() : nav('#/home'); }
  else if (k === 'pick-a') picker('a'); else if (k === 'pick-b') picker('b');
  else if (k === 'kebab') sheet(BY[v].name, `<button class="act" data-act="open:${v}">상세 보기</button><button class="act" data-act="edit:b:${v}">평형·층대 변경</button><button class="act" data-act="plan:${v}">이 후보로 자금 계획</button><button class="act danger" data-act="del:${v}">후보에서 삭제</button>`);
  else if (k === 'kebab-a') sheet(BY[st.a.id].name, `<button class="act" data-act="open:${st.a.id}">상세 보기</button><button class="act" data-act="edit:a:${st.a.id}">평형·층 변경</button><button class="act" data-act="pick-a">다른 단지로 변경</button><button class="act" data-act="own">취득 정보 입력·수정</button>`);
  else if (k === 'edit') editSheet(v, w);
  else if (k === 'savetype') { if (st.a && st.a.id === v) st.a.type = +w; else (st.bs || []).forEach(b => { if (b.id === v) { b.type = +w; b.sample = false; } }); save(); render(true); }
  else if (k === 'open') { closeSheet(); nav('#/c/' + v); } else if (k === 'plan') { closeSheet(); nav('#/plan?b=' + v); }
  else if (k === 'del') { st.bs = st.bs.filter(b => b.id !== v); if (!st.bs.length) st.bs = []; save(); closeSheet(); render(); }
  else if (k === 'theme') { st.theme = v; save(); applyTheme(); render(); }
  else if (k === 'commit') commit();
  else if (k === 'own') ownSheet();
  else if (k === 'own-save') { const b = +($('#ob').value || '').replace(/[^0-9]/g, ''), y = $('#oy').value; if (b > 0) { st.a.buy = b; st.a.ym = /^\d{4}-\d\d$/.test(y) ? y : null; save(); closeSheet(); render(); } }
  else if (k === 'own-clear') { delete st.a.buy; delete st.a.ym; save(); closeSheet(); render(); }
  else if (k === 'intro') { st.intro = 1; save(); render(); if (v === 'pick') picker('a'); }
  else if (k === 'floc') { locSheet(); }
  else if (k === 'loc') { const L = st.find.locs, i = L.indexOf(String(v)); L.splice(0, L.length, ...L.filter(l => !l.startsWith(v + ':') && l !== String(v))); if (i < 0) L.push(String(v)); save(); w === 'back' ? dongSheet(v) : locSheet(); }
  else if (k === 'dong') dongSheet(v);
  else if (k === 'dloc') { const L = st.find.locs, key = v + ':' + w, i = L.indexOf(key); L.splice(0, L.length, ...L.filter(l => l !== String(v) && l !== key)); if (i < 0) L.push(key); save(); dongSheet(v); }
  else if (k === 'fdone') { closeSheet(); save(); render(true); }
  else if (k === 'fmode') { st.find.mode = v; save(); render(true); }
  else if (k === 'frange') { st.find.range = +v; save(); render(true); }
  else if (k === 'fcls') { st.find.cls[v] = st.find.cls[v] ? 0 : 1; save(); render(true); }
  else if (k === 'fsort') { st.find.sort = v; save(); render(true); }
  else if (k === 'ftohu') { st.find.tohu = st.find.tohu ? 0 : 1; save(); render(true); }
  else if (k === 'fadd') { addB(v, w); if (/^#\/c\//.test(location.hash)) render(true); else { const b = document.querySelector(`[data-act="fadd:${v}:${w}"]`); if (b) b.textContent = '추가됨 ✓'; } }
  else if (k === 'fplan') { addB(v, w); const t = (CAND[v] || []).find(x => x[0] === +w), P = Pof(FC.xa); nav('#/plan?b=' + v + (st.find.mode === 'gap' && t ? `&jeonse=${r1(t[3] * P.jr / 100)}&rent=${P.rent}` : '')); }
  else if (k === 'unit') { st.unit = v === 'py' ? 'py' : 'm2'; save(); render(true); }
  else if (k === 'tour') { if (v === 'end') closeSheet(); else tourStep(+v); }
  else if (k === 'aloc') { AQ = ''; areaSheet(); } else if (k === 'adone') { closeSheet(); render(true); }
  else if (k === 'adong') areaDongSheet(v);
  else if (k === 'at' || k === 'atd') { atog(k === 'at' ? String(v) : v + ':' + w); if ($('#sheet').classList.contains('on')) { if ($('#aq')) areaList(); else if (k === 'at' && w === 'back') areaDongSheet(v); else if (k === 'atd') areaDongSheet(v); else areaSheet(); } else render(true); }
  else if (k === 'reset') { st = DEF(); save(); applyTheme(); nav('#/home'); render(); }
}
document.addEventListener('click', e => {
  const t = e.target.closest('[data-act],[data-go],[data-pick],[data-ty],[data-tr]'); if (!t) { if (e.target.id === 'bd') closeSheet(); return; }
  e.stopPropagation();
  if (t.dataset.pick) { const [role, id] = t.dataset.pick.split(':'); step2(role, id).catch(fail); }
  else if (t.dataset.ty) { PEND.type = +t.dataset.ty; document.querySelectorAll('#ty button').forEach(b => b.classList.toggle('on', b === t)); }
  else if (t.dataset.tr) { PEND.tier = +t.dataset.tr; document.querySelectorAll('#tr button').forEach(b => b.classList.toggle('on', b === t)); }
  else if (t.dataset.act) act(t.dataset.act); else if (t.dataset.go) { closeSheet(); nav(t.dataset.go); }
});
function tipAt(e) {
  const tip = $('#tip'), sv = e.target.closest && e.target.closest('#chart'); if (!tip) return;
  if (!sv || !CH) { tip.style.opacity = 0; return; }
  const r = sv.getBoundingClientRect(), x = (e.clientX - r.left) * CH.W / r.width; let best = null;
  for (const d of CH.dots) { const dx = Math.abs(CH.X(d.m) - x); if (dx < 7 && (!best || dx < best.dx)) best = { dx, d }; }
  const m = Math.max(-CH.months, Math.min(0, (x - CH.pl) / (CH.W - CH.pl - CH.pr) * CH.months - CH.months)), p = CH.pts, i = Math.min(p.length - 2, Math.max(0, p.findIndex(q => q[0] > m) - 1 < 0 ? p.length - 2 : p.findIndex(q => q[0] > m) - 1)), f = (m - p[i][0]) / (p[i + 1][0] - p[i][0]), v = k => p[i][k] + (p[i + 1][k] - p[i][k]) * f;
  tip.innerHTML = best ? `<b>거래 ${won(best.d.amt)}</b><br>${dateOf(IDX.meta.end_ord + best.d.dt)} · ${best.d.fl}층` : `<b>추세선 ${won(v(1))}</b><br>${dateOf(IDX.meta.end_ord + m * 30.4)} · 범위 ${won(v(2))} ~ ${won(v(3))}`;
  const w = sv.parentElement.getBoundingClientRect(); tip.style.left = Math.max(70, Math.min(w.width - 70, e.clientX - w.left)) + 'px'; tip.style.opacity = 1;
}
document.addEventListener('pointermove', tipAt); document.addEventListener('pointerdown', tipAt);
document.addEventListener('keydown', e => { if (e.key === 'Escape' && $('#sheet').classList.contains('on')) closeSheet(); if ((e.key === 'Enter' || e.key === ' ') && e.target.matches && e.target.matches('[role=button]:not(button)')) { e.preventDefault(); e.target.click(); } });
document.addEventListener('change', e => { if (e.target.id === 'fsort') { st.find.sort = e.target.value; save(); render(true); } });
document.addEventListener('input', e => {
  if (e.target.id === 'aq') { AQ = e.target.value; areaList(); return; }
  const f = e.target.closest && e.target.closest('input[data-fk]');
  if (f && FC) { const k = f.dataset.fk, v = f.value.replace(/[^0-9.]/g, ''); f.value = v; if (v === '' && (k === 'sale' || k === 'income')) delete st.plan[k]; else st.plan[k] = parseFloat(v) || 0; save(); $('#fres').innerHTML = fresHtml(); return; }
  const i = e.target.closest('.field input'); if (!i || !PC) return;
  const k = i.dataset.k, v = i.value.replace(/[^0-9]/g, ''); i.value = v;
  if (v === '' && (k === 'sale' || k === 'buy')) delete st.plan[k]; else st.plan[k] = +v || 0;
  PC.p[k] = v === '' && (k === 'sale' || k === 'buy') ? (k === 'sale' ? (PC.ea || [0])[0] : (PC.eb || [0])[0]) : +v || 0; save();
  if (k === 'cash') PC.cashSet = true;
  $('#res').innerHTML = planResult(PC); const ps = $('#pstick'); if (ps) ps.innerHTML = planStick(PC);
  const fm = i.closest('.field').querySelector('[data-fm]'); if (fm) fm.textContent = PC.p[k] > 0 ? won(Math.round(PC.p[k])) : '';
});
$('#fab').addEventListener('click', () => sheet('후보 추가', `<button class="act" data-act="pick-b">단지 이름으로 직접 검색</button><button class="act" data-go="#/find">입지 고르고 조건으로 찾기 ›</button>`));
window.addEventListener('hashchange', () => render());

/* ---------- 시작 ---------- */
fetch(dq('data/index.json')).then(r => { if (!r.ok) throw new Error('data ' + r.status); return r.json(); }).then(d => {
  IDX = d; d.c.forEach(c => BY[c.id] = c); return render();
}).then(() => {
  const sp = $('#splash'), skip = /nosplash/.test(location.search) || sessionStorage.getItem('a2b.splash');
  if (skip) sp.remove(); else { sessionStorage.setItem('a2b.splash', '1'); setTimeout(() => sp.classList.add('off'), 1100); setTimeout(() => sp.remove(), 1600); }
  if (/[?&]tour=1/.test(location.search)) setTimeout(() => tourStep(0), 300);
  else if (!st.tour && !/nosplash/.test(location.search) && !/sheet=/.test(location.hash)) { st.tour = 1; save(); setTimeout(() => tourStep(0), skip ? 500 : 1800); }   // 처음 방문 때 한 번만
}).catch(e => { fail(e); const sp = $('#splash'); if (sp) sp.remove(); });
})();
