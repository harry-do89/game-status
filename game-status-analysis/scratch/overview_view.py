"""
"Game Production Overview" view for the Game Status dashboard.

Exports OVERVIEW_CSS, OVERVIEW_HTML, OVERVIEW_JS — injected into the page by
generate_game_status_html.py via {{OVERVIEW_CSS}}, {{OVERVIEW_HTML}}, {{OVERVIEW_JS}}.

A dark "production-cockpit" dashboard rendered client-side from the `gs-overview`
JSON block (built by scratch/overview_logic.py). It is the default view; the SVG
flow graph lives behind the top toggle. Cards reuse the shared openTimelineModal().

Layout fits a single dense 12-col grid; the long lists (actions, deadlines, health)
scroll *internally* so the page itself stays close to one viewport.
"""

# Semantic colours shared by Python comments and JS below:
#   late #ef4444 · risk #f59e0b · ontrack #10b981 · done #5b6470 · accent #5b8cff

OVERVIEW_CSS = """\
  /* ── View toggle (global, sits above both views) ─────────────────────────── */
  #vt-bar { position: sticky; top: 0; z-index: 60; display: flex; align-items: center;
            gap: 16px; padding: 10px 20px; background: #0b0d11; border-bottom: 1px solid #1d222b;
            font-family: 'Sora', system-ui, sans-serif; }
  #vt-switch { display: inline-flex; background: #14181f; border: 1px solid #232a34;
               border-radius: 999px; padding: 3px; }
  .vt-btn { border: none; background: transparent; color: #8b95a3; font-family: inherit;
            font-weight: 600; font-size: 0.8rem; padding: 8px 36px; min-width: 140px;
            text-align: center; border-radius: 999px; cursor: pointer; transition: all .15s; }
  .vt-btn.active { background: #5b8cff; color: #fff; box-shadow: 0 2px 12px rgba(91,140,255,.4); }
  .vt-btn:not(.active):hover { color: #e7ecf3; }
  #vt-spacer { flex: 1; }
  #vt-asof { font-family: 'IBM Plex Mono', monospace; font-size: 0.74rem; color: #5f6b7a;
             letter-spacing: 0.02em; }

  /* ── Overview shell ──────────────────────────────────────────────────────── */
  #view-overview {
    --late: #ef4444; --risk: #f59e0b; --ontrack: #10b981; --done: #5b6470; --accent: #5b8cff;
    --bg: #0f1115; --card: #181b21; --card2: #1d2129; --line: #262b33;
    --ink: #e7ecf3; --ink2: #9aa4b2; --ink3: #5f6b7a;
    background: radial-gradient(1200px 600px at 80% -10%, #161b24 0%, #0f1115 55%);
    min-height: calc(100vh - 49px); padding: 12px 20px 20px;
    font-family: 'IBM Plex Sans', system-ui, sans-serif; color: var(--ink);
  }
  #view-overview h3 { font-family: 'Sora', system-ui, sans-serif; font-size: 0.7rem;
                      font-weight: 600; letter-spacing: 0.12em; text-transform: uppercase;
                      color: var(--ink3); margin: 0; }
  .ov-num { font-family: 'IBM Plex Mono', monospace; font-variant-numeric: tabular-nums; }

  /* Header */
  .ov-header { display: flex; align-items: flex-end; justify-content: space-between;
               margin-bottom: 10px; }
  .ov-title { font-family: 'Sora', sans-serif; font-size: 1.18rem; font-weight: 700;
              letter-spacing: 0.01em; }
  .ov-legend { display: flex; gap: 14px; font-size: 0.72rem; color: var(--ink2); }
  .ov-leg { display: flex; align-items: center; gap: 6px; }
  .ov-leg i { width: 9px; height: 9px; border-radius: 3px; display: inline-block; }

  /* Card primitive */
  .ov-card { position: relative; background:
               linear-gradient(180deg, rgba(255,255,255,.025), rgba(255,255,255,0) 40%), var(--card);
             border: 1px solid var(--line); border-radius: 14px; padding: 14px 16px;
             transition: border-color .15s, transform .15s; }
  .ov-card-head { display: flex; align-items: center; justify-content: space-between;
                  margin-bottom: 10px; gap: 10px; }
  .ov-scroll { max-height: 168px; overflow-y: auto; margin: -2px -6px -2px 0; padding-right: 6px; }
  .ov-scroll::-webkit-scrollbar { width: 7px; }
  .ov-scroll::-webkit-scrollbar-thumb { background: #2c333d; border-radius: 4px; }
  .ov-scroll::-webkit-scrollbar-track { background: transparent; }

  /* KPI strip */
  .ov-kpis { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 12px; }
  .kpi { padding: 11px 16px; opacity: 0; transform: translateY(8px);
         animation: ov-rise .5s cubic-bezier(.2,.7,.3,1) forwards; }
  .kpi:nth-child(2){animation-delay:.05s} .kpi:nth-child(3){animation-delay:.1s} .kpi:nth-child(4){animation-delay:.15s}
  .kpi-label { font-size: 0.72rem; color: var(--ink2); letter-spacing: 0.03em; }
  .kpi-val { font-size: 1.85rem; font-weight: 600; line-height: 1.05; margin: 4px 0 2px;
             font-family: 'IBM Plex Mono', monospace; font-variant-numeric: tabular-nums; }
  .kpi-foot { font-size: 0.7rem; color: var(--ink3); white-space: nowrap; overflow: hidden;
              text-overflow: ellipsis; }
  .kpi.k-total .kpi-val { color: var(--accent); }
  .kpi.k-late  .kpi-val { color: var(--late); }   .kpi.k-late .kpi-foot  { color: #c4534f; }
  .kpi.k-risk  .kpi-val { color: var(--risk); }   .kpi.k-risk .kpi-foot  { color: #b07f33; }
  .kpi.k-ok    .kpi-val { color: var(--ontrack); }.kpi.k-ok .kpi-foot    { color: #4e8a6f; }

  /* Main grid */
  .ov-grid { display: grid; grid-template-columns: repeat(12, 1fr); gap: 12px; align-items: start; }
  .ov-pipeline  { grid-column: span 5; }
  .ov-actions   { grid-column: span 7; }
  .ov-health    { grid-column: span 7; }
  .ov-deadlines { grid-column: span 5; }
  .ov-delay     { grid-column: span 12; }
  @media (max-width: 1080px){
    .ov-pipeline,.ov-actions,.ov-health,.ov-deadlines,.ov-delay{ grid-column: span 12; }
    .ov-kpis{ grid-template-columns: repeat(2,1fr); }
  }

  /* Pipeline health rows */
  .pl-row { display: grid; grid-template-columns: 118px 1fr 26px auto; align-items: center;
            gap: 10px; padding: 5px 0; }
  .pl-name { font-size: 0.8rem; color: var(--ink); white-space: nowrap; overflow: hidden;
             text-overflow: ellipsis; }
  .pl-track { height: 7px; background: #20252e; border-radius: 6px; overflow: hidden; }
  .pl-fill { height: 100%; border-radius: 6px; transition: width .5s cubic-bezier(.2,.7,.3,1); }
  .pl-cnt { font-size: 0.84rem; text-align: right; color: var(--ink); }
  .pl-badge { font-size: 0.66rem; font-weight: 700; padding: 2px 7px; border-radius: 6px;
              white-space: nowrap; }
  .pl-badge.late { background: rgba(239,68,68,.16); color: #f7a3a1; }
  .pl-badge.risk { background: rgba(245,158,11,.16); color: #f3c277; }
  .pl-badge.zero { color: var(--ink3); }

  /* Action list / deadline list */
  .li { display: flex; align-items: center; gap: 10px; padding: 8px 6px; border-radius: 8px;
        cursor: pointer; transition: background .12s; }
  .li:hover { background: rgba(255,255,255,.04); }
  .li + .li { border-top: 1px solid #20252e; }
  .li-ic { width: 20px; height: 20px; flex-shrink: 0; display: grid; place-items: center;
           border-radius: 6px; font-size: 0.72rem; }
  .li-ic.flag { background: rgba(239,68,68,.15); color: var(--late); }
  .li-ic.warn { background: rgba(245,158,11,.15); color: var(--risk); }
  .li-ic.clock{ background: rgba(91,140,255,.14); color: var(--accent); }
  .li-key { font-family: 'IBM Plex Mono', monospace; font-size: 0.8rem; font-weight: 600;
            color: var(--ink); flex-shrink: 0; }
  .li-mid { flex: 1; min-width: 0; font-size: 0.76rem; color: var(--ink2);
            white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .li-tag { font-size: 0.74rem; font-weight: 600; white-space: nowrap; }
  .li-tag.late { color: var(--late); } .li-tag.risk { color: var(--risk); }
  .li-tag.ontrack { color: var(--ontrack); } .li-tag.muted { color: var(--ink3); }

  /* Group health rows */
  .gh-row { display: grid; grid-template-columns: 96px 1fr auto; align-items: center;
            gap: 10px; padding: 7px 0; }
  .gh-row + .gh-row { border-top: 1px solid #20252e; }
  .gh-name { font-size: 0.8rem; font-weight: 600; color: var(--ink); white-space: nowrap;
             overflow: hidden; text-overflow: ellipsis; }
  .gh-sq { display: flex; flex-wrap: wrap; gap: 3px; }
  .gh-sq i { width: 11px; height: 11px; border-radius: 3px; display: inline-block;
             transform: scale(0); animation: ov-pop .3s ease forwards; }
  .gh-tag { font-size: 0.72rem; font-weight: 600; white-space: nowrap; text-align: right; }

  /* Delay stacked column chart */
  .dc { display: grid; grid-template-columns: 26px 1fr; gap: 4px; }
  .dc-yaxis { position: relative; height: 240px; }
  .dc-yaxis span { position: absolute; right: 3px; font-family: 'IBM Plex Mono', monospace;
                   font-size: 9px; color: var(--ink3); transform: translateY(50%); }
  .dc-yaxis span::after { content: ''; position: absolute; right: -6px; top: 50%; width: 5px;
                          border-top: 1px solid var(--line); }
  .dc-plot { position: relative; display: flex; align-items: flex-end; gap: 6px; height: 240px;
             overflow-x: auto; padding: 0 4px; border-left: 1px solid var(--line); }
  .dc-plot::-webkit-scrollbar { height: 7px; }
  .dc-plot::-webkit-scrollbar-thumb { background: #2c333d; border-radius: 4px; }
  .dc-col { flex: 1 1 0; min-width: 34px; max-width: 80px; height: 100%; display: flex;
            flex-direction: column; align-items: center; justify-content: flex-end; }
  .dc-stack { display: flex; flex-direction: column-reverse; width: 100%; border-radius: 4px 4px 0 0;
              overflow: hidden; }
  .dc-seg { width: 100%; transition: height .5s cubic-bezier(.2,.7,.3,1); }
  .dc-cap { font-family: 'IBM Plex Mono', monospace; font-size: 9px; color: var(--ink2); margin-bottom: 3px; }
  .dc-xlabel { height: 16px; line-height: 16px; margin-top: 5px; font-size: 9px; color: var(--ink2);
               max-width: 80px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; text-align: center; }
  .dc-legend { display: flex; flex-wrap: wrap; gap: 14px; margin-top: 10px; font-size: 0.72rem; color: var(--ink2); }
  .dc-legend .ov-leg i { width: 9px; height: 9px; border-radius: 3px; display: inline-block; }
  .dc-col { cursor: default; }
  /* Chart.js-style tooltip: dark translucent box + caret, like the Verticals
     "Weekly Intake vs Resolved" chart's default tooltip. */
  .dc-tip { position: fixed; z-index: 200; background: rgba(10,12,16,.92);
            border-radius: 6px; padding: 8px 10px; min-width: 128px; pointer-events: none;
            opacity: 0; transform: translate(-50%, calc(-100% - 11px)); transition: opacity .1s;
            font-family: 'IBM Plex Sans', system-ui, sans-serif; }
  .dc-tip::after { content: ''; position: absolute; left: 50%; bottom: -5px; width: 10px; height: 5px;
                   transform: translateX(-50%); background: rgba(10,12,16,.92);
                   clip-path: polygon(0 0, 100% 0, 50% 100%); }
  .dc-tip.show { opacity: 1; }
  .dc-tip-name { font-size: 0.72rem; font-weight: 600; color: #fff; margin-bottom: 4px; }
  .dc-tip-row { display: flex; align-items: center; gap: 6px; font-size: 0.72rem; color: #f8fafc;
                padding: 2px 0; }
  .dc-tip-row i { width: 8px; height: 8px; border-radius: 1px; flex-shrink: 0; }
  .dc-tip-row b { margin-left: auto; font-weight: 600; }
  .dc-tip-total { margin-top: 4px; padding-top: 4px; border-top: 1px solid rgba(255,255,255,.14);
                  font-size: 0.72rem; color: #cbd5e1; display: flex; justify-content: space-between; }
  .dc-tip-total b { color: #fff; }

  /* Sub-tabs */
  .ov-tabs { display: inline-flex; gap: 2px; background: #14181f; border: 1px solid #232a34;
             border-radius: 8px; padding: 2px; }
  .ov-tab { border: none; background: transparent; color: var(--ink3); font-family: inherit;
            font-size: 0.72rem; font-weight: 600; padding: 4px 11px; border-radius: 6px; cursor: pointer; }
  .ov-tab.active { background: #2a313c; color: var(--ink); }

  .ov-empty { color: var(--ink3); font-size: 0.78rem; padding: 18px 4px; text-align: center; }

  @keyframes ov-rise { to { opacity: 1; transform: none; } }
  @keyframes ov-pop  { to { transform: scale(1); } }
"""

OVERVIEW_HTML = """\
<div id="view-overview">
  <div class="ov-header">
    <div>
      <div class="ov-title" id="ov-title">Today's Overview</div>
    </div>
    <div class="ov-legend">
      <span class="ov-leg"><i style="background:#ef4444"></i>Late</span>
      <span class="ov-leg"><i style="background:#f59e0b"></i>At Risk</span>
      <span class="ov-leg"><i style="background:#10b981"></i>On Track</span>
      <span class="ov-leg"><i style="background:#5b6470"></i>Done</span>
    </div>
  </div>

  <div class="ov-kpis" id="ov-kpis"></div>

  <div class="ov-grid">
    <section class="ov-card ov-pipeline">
      <div class="ov-card-head"><h3>Pipeline Health</h3></div>
      <div id="ov-pipeline"></div>
    </section>

    <section class="ov-card ov-actions">
      <div class="ov-card-head"><h3>Action Needed</h3></div>
      <div class="ov-scroll" id="ov-actions"></div>
    </section>

    <section class="ov-card ov-health">
      <div class="ov-card-head"><h3>Group Health</h3><div class="ov-tabs" id="ov-health-tabs"></div></div>
      <div class="ov-scroll" id="ov-health"></div>
    </section>

    <section class="ov-card ov-deadlines">
      <div class="ov-card-head"><h3>Deadlines &mdash; Next 30 Days</h3></div>
      <div class="ov-scroll" id="ov-deadlines"></div>
    </section>

    <section class="ov-card ov-delay">
      <div class="ov-card-head"><h3>Delay Status by Group</h3><div class="ov-tabs" id="ov-delay-tabs"></div></div>
      <div id="ov-delay"></div>
    </section>
  </div>
</div>
"""

OVERVIEW_JS = """\
  // ── Overview dashboard ──────────────────────────────────────────────────────
  const OV = JSON.parse(document.getElementById('gs-overview').textContent);
  const OV_COLOR = { late:'#ef4444', risk:'#f59e0b', ontrack:'#10b981', done:'#5b6470' };

  function ovDateVN(iso){
    if(!iso) return '\\u2014';
    const p = iso.substring(0,10).split('-');
    return p.length === 3 ? p[2]+'/'+p[1]+'/'+p[0] : iso;
  }

  // "YYYY-MM-DD HH:MM:SS" -> "DD/MM/YYYY HH:MM" (last pipeline sync timestamp).
  function ovSyncLabel(raw){
    if(!raw) return '\\u2014';
    const [d, t] = raw.split(' ');
    return ovDateVN(d) + (t ? ' ' + t.slice(0,5) : '');
  }

  function ovCountUp(el, target){
    const dur = 600, t0 = performance.now();
    function step(now){
      const k = Math.min((now - t0) / dur, 1);
      el.textContent = Math.round(target * (1 - Math.pow(1 - k, 3)));
      if(k < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  }

  function ovOpenCard(key){
    const g = (OV.by_key || {})[key];
    if(!g){ return; }
    openTimelineModal(key, { summary: g.summary, studio: g.studio, market: g.market,
      batch: g.batch, category: g.category, wishful: g.wishful, status: g.status, created: g.created });
  }

  function ovKpiCard(cls, label, val, foot){
    return '<div class="ov-card kpi '+cls+'">'+
      '<div class="kpi-label">'+esc(label)+'</div>'+
      '<div class="kpi-val ov-num" data-count="'+val+'">0</div>'+
      '<div class="kpi-foot">'+foot+'</div></div>';
  }

  function ovKeysFoot(keys, suffix){
    if(!keys || !keys.length) return suffix || '&mdash;';
    const head = keys.slice(0,2).map(esc).join(', ');
    return head + (keys.length > 2 ? '&hellip;' : '');
  }

  function renderOverview(){
    document.getElementById('ov-title').textContent = "Today's Overview - " + ovDateVN(OV.as_of);
    document.getElementById('vt-asof').textContent = 'Synced ' + ovSyncLabel(OV.last_sync);

    // KPI strip
    const k = OV.kpi;
    document.getElementById('ov-kpis').innerHTML =
      ovKpiCard('k-total','Total Active Games', k.active, 'in pipeline') +
      ovKpiCard('k-late','Late', k.late, ovKeysFoot(k.late_keys,'none')) +
      ovKpiCard('k-risk','At Risk', k.risk, ovKeysFoot(k.risk_keys,'none')) +
      ovKpiCard('k-ok','On Track', k.ontrack,
                (k.active ? Math.round(k.ontrack / k.active * 100) : 0) + '% of total');
    document.querySelectorAll('#ov-kpis .kpi-val').forEach(el =>
      ovCountUp(el, parseInt(el.dataset.count, 10) || 0));

    renderPipeline();
    renderActions();
    renderDeadlines();
    buildTabs('ov-health-tabs', renderHealth);
    buildTabs('ov-delay-tabs', renderDelay);
  }

  function renderPipeline(){
    const rows = OV.pipeline;
    const max = Math.max(1, ...rows.map(r => r.count));
    document.getElementById('ov-pipeline').innerHTML = rows.map(r => {
      const color = r.late ? OV_COLOR.late : (r.risk ? OV_COLOR.risk : '#3a434f');
      const w = (r.count / max * 100).toFixed(0);
      let badge = '<span class="pl-badge zero"></span>';
      if(r.late) badge = '<span class="pl-badge late">'+r.late+' late</span>';
      else if(r.risk) badge = '<span class="pl-badge risk">'+r.risk+' at risk</span>';
      return '<div class="pl-row">'+
        '<span class="pl-name">'+esc(r.stage)+'</span>'+
        '<span class="pl-track"><span class="pl-fill" style="width:'+(r.count?w:0)+'%;background:'+color+'"></span></span>'+
        '<span class="pl-cnt ov-num">'+r.count+'</span>'+ badge +'</div>';
    }).join('');
  }

  function renderActions(){
    const items = OV.actions;
    const el = document.getElementById('ov-actions');
    if(!items.length){ el.innerHTML = '<div class="ov-empty">No actions needed 🎉</div>'; return; }
    el.innerHTML = items.map(a => {
      const ic = a.reason_kind === 'flag' ? 'flag' : 'warn';
      const sym = a.reason_kind === 'flag' ? '\\u2691' : '\\u26A0';
      return '<div class="li" onclick="ovOpenCard(\\''+esc(a.key)+'\\')">'+
        '<span class="li-ic '+ic+'">'+sym+'</span>'+
        '<span class="li-key">'+esc(a.key)+'</span>'+
        '<span class="li-mid">'+esc(a.status)+'</span>'+
        '<span class="li-tag '+a.bucket+'">'+esc(a.reason)+'</span></div>';
    }).join('');
  }

  function renderDeadlines(){
    const items = OV.deadlines;
    const el = document.getElementById('ov-deadlines');
    if(!items.length){ el.innerHTML = '<div class="ov-empty">No deadlines in the next 30 days</div>'; return; }
    el.innerHTML = items.map(d => {
      let tag, cls;
      if(d.days_left < 0){ tag = (-d.days_left) + 'd late'; cls = 'late'; }
      else if(d.days_left === 0){ tag = 'today'; cls = 'late'; }
      else if(d.days_left <= 7){ tag = d.days_left + 'd left'; cls = 'risk'; }
      else { tag = d.days_left + 'd left'; cls = 'ontrack'; }
      return '<div class="li" onclick="ovOpenCard(\\''+esc(d.key)+'\\')">'+
        '<span class="li-ic clock">\\u25CB</span>'+
        '<span class="li-key">'+esc(d.key)+'</span>'+
        '<span class="li-mid">'+esc(d.summary)+'</span>'+
        '<span class="li-tag muted">'+esc(d.studio || '\\u2014')+'</span>'+
        '<span class="li-tag '+cls+'">'+tag+'</span></div>';
    }).join('');
  }

  // Group sub-tabs (shared builder for health + delay cards).
  const ovTabState = {};
  function buildTabs(containerId, renderFn){
    const fields = OV.group_fields;
    const cont = document.getElementById(containerId);
    ovTabState[containerId] = ovTabState[containerId] || fields[0];
    cont.innerHTML = fields.map(f =>
      '<button class="ov-tab'+(f===ovTabState[containerId]?' active':'')+'" data-f="'+esc(f)+'">'+esc(f)+'</button>'
    ).join('');
    cont.querySelectorAll('.ov-tab').forEach(btn => btn.onclick = () => {
      ovTabState[containerId] = btn.dataset.f;
      cont.querySelectorAll('.ov-tab').forEach(b => b.classList.toggle('active', b===btn));
      renderFn();
    });
    renderFn();
  }

  function renderHealth(){
    const field = ovTabState['ov-health-tabs'];
    const groups = OV.groups[field] || [];
    const el = document.getElementById('ov-health');
    if(!groups.length){ el.innerHTML = '<div class="ov-empty">No data</div>'; return; }
    el.innerHTML = groups.map(g => {
      const sq = g.items.slice(0, 24).map((it, i) =>
        '<i style="background:'+OV_COLOR[it.bucket]+';animation-delay:'+(i*18)+'ms"></i>').join('');
      const bits = [];
      if(g.late) bits.push('<span style="color:#ef4444">'+g.late+' late</span>');
      if(g.risk) bits.push('<span style="color:#f59e0b">'+g.risk+' at risk</span>');
      const tag = bits.length ? bits.join(' · ') : '<span style="color:#10b981">OK</span>';
      return '<div class="gh-row">'+
        '<span class="gh-name">'+esc(g.name || '\\u2014')+'</span>'+
        '<span class="gh-sq">'+sq+'</span>'+
        '<span class="gh-tag">'+tag+'</span></div>';
    }).join('');
  }

  function renderDelay(){
    const field = ovTabState['ov-delay-tabs'];
    const groups = OV.groups[field] || [];
    const el = document.getElementById('ov-delay');
    if(!groups.length){ el.innerHTML = '<div class="ov-empty">No data</div>'; return; }

    const order = ['late','risk','ontrack','done'];   // stacked bottom → top
    const maxT = Math.max(1, ...groups.map(g => g.total));
    const BAR = 206, LABEL = 21;                       // px: plot height / x-label band

    // Vertical stacked columns, one per group.
    const cols = groups.map((g, i) => {
      const segs = order.filter(b => g[b] > 0).map(b =>
        '<span class="dc-seg" style="height:'+(g[b]/maxT*BAR).toFixed(1)+'px;background:'+OV_COLOR[b]+'"></span>'
      ).join('');
      return '<div class="dc-col" data-i="'+i+'">'+
        '<span class="dc-cap">'+g.total+'</span>'+
        '<div class="dc-stack">'+segs+'</div>'+
        '<div class="dc-xlabel">'+esc(g.name || '\\u2014')+'</div></div>';
    }).join('');

    // Y-axis ticks (nice-ish): max, mid, 0 — deduped for small ranges.
    const ticks = [...new Set([maxT, Math.round(maxT/2), 0])].map(v =>
      '<span style="bottom:'+(LABEL + v/maxT*BAR).toFixed(0)+'px">'+v+'</span>').join('');

    el.innerHTML =
      '<div class="dc">'+
        '<div class="dc-yaxis">'+ticks+'</div>'+
        '<div class="dc-plot">'+cols+'</div>'+
      '</div>'+
      '<div class="dc-legend">'+
        '<span class="ov-leg"><i style="background:#ef4444"></i>Late</span>'+
        '<span class="ov-leg"><i style="background:#f59e0b"></i>At Risk</span>'+
        '<span class="ov-leg"><i style="background:#10b981"></i>On Track</span>'+
        '<span class="ov-leg"><i style="background:#5b6470"></i>Done</span>'+
      '</div>';

    const tip = ovDelayTip();
    const LBL = { late:'Late', risk:'At Risk', ontrack:'On Track', done:'Done' };
    el.querySelectorAll('.dc-col').forEach(col => {
      const g = groups[parseInt(col.dataset.i, 10)];
      const rows = order.filter(b => g[b] > 0).map(b =>
        '<div class="dc-tip-row"><i style="background:'+OV_COLOR[b]+'"></i>'+LBL[b]+'<b>'+g[b]+'</b></div>'
      ).join('');
      col.onmouseenter = col.onmousemove = (ev) => {
        tip.innerHTML = '<div class="dc-tip-name">'+esc(g.name || '\\u2014')+'</div>'+rows+
          '<div class="dc-tip-total">Total<b>'+g.total+'</b></div>';
        tip.style.left = ev.clientX + 'px';
        tip.style.top = (ev.clientY - 12) + 'px';
        tip.classList.add('show');
      };
      col.onmouseleave = () => tip.classList.remove('show');
    });
  }

  function ovDelayTip(){
    let tip = document.getElementById('dc-tip');
    if(!tip){
      tip = document.createElement('div');
      tip.id = 'dc-tip';
      tip.className = 'dc-tip';
      document.body.appendChild(tip);
    }
    return tip;
  }

  // ── View toggle ─────────────────────────────────────────────────────────────
  function setView(view){
    const isOv = view === 'overview';
    document.getElementById('view-overview').style.display = isOv ? '' : 'none';
    document.getElementById('view-flow').style.display = isOv ? 'none' : '';
    document.querySelectorAll('.vt-btn').forEach(b => b.classList.toggle('active', b.dataset.view === view));
    document.body.style.background = isOv ? '#0f1115' : '#f1f5f9';
    try { localStorage.setItem('gamestatus_view', view); } catch(e){}
  }
  document.querySelectorAll('.vt-btn').forEach(b => b.onclick = () => setView(b.dataset.view));

  renderOverview();
  (function(){
    let v = 'overview';
    try { v = localStorage.getItem('gamestatus_view') || 'overview'; } catch(e){}
    setView(v);
  })();
"""
