"""Dark Control Center UI injected into the Flow tab."""

CC_CSS = r"""
  #view-flow {
    --cc-bg:#0a0e17; --cc-panel:#121829; --cc-panel-2:#1a2236; --cc-hair:#28324c;
    --cc-violet:#7b6ef6; --cc-green:#2fd6a0; --cc-amber:#f5a524; --cc-danger:#ef5d6b;
    --cc-cyan:#22d3ee; --cc-blue:#4b8bf5; --cc-text:#e9edf6; --cc-muted:#8b95ad;
    --cc-muted-2:#5c6680; --cc-display:'Space Grotesk',system-ui,sans-serif;
    --cc-body:'Inter',system-ui,sans-serif; --cc-mono:'JetBrains Mono',ui-monospace,monospace;
    background:radial-gradient(900px 420px at 78% -10%, rgba(123,110,246,.14), transparent 60%), var(--cc-bg);
    color:var(--cc-text); font-family:var(--cc-body); min-height:calc(100vh - 58px);
  }
  #view-flow * { box-sizing:border-box; }
  #view-flow .cc-wrap { max-width:1360px; margin:0 auto; padding:28px 28px 90px; }
  #view-flow .cc-topline { display:flex; justify-content:space-between; align-items:flex-end; gap:12px; flex-wrap:wrap; }
  #view-flow .cc-topline h1 { font-family:var(--cc-display); font-size:28px; line-height:1.1; margin:0; letter-spacing:0; }
  #view-flow .cc-dot { color:var(--cc-violet); }
  #view-flow .cc-gen { font-family:var(--cc-mono); color:var(--cc-muted); font-size:11.5px; letter-spacing:.3px; }
  #view-flow .cc-filters { position:sticky; top:52px; z-index:30; margin:16px 0 22px; padding:12px 16px; display:flex;
    gap:10px 18px; flex-wrap:wrap; align-items:center; background:rgba(12,17,28,.9); backdrop-filter:blur(12px);
    border:1px solid var(--cc-hair); border-radius:14px; box-shadow:0 8px 24px rgba(0,0,0,.25); }
  #view-flow .cc-fgroup { display:flex; align-items:center; gap:7px; flex-wrap:wrap; }
  #view-flow .cc-flabel { font-family:var(--cc-mono); font-size:10.5px; color:var(--cc-muted-2); text-transform:uppercase; letter-spacing:.7px; }
  #view-flow .cc-fdiv { width:1px; height:24px; background:var(--cc-hair); }
  #view-flow .cc-chip { display:inline-flex; align-items:center; gap:6px; min-height:30px; background:var(--cc-panel-2);
    border:1px solid var(--cc-hair); color:var(--cc-muted); border-radius:8px; padding:5px 10px; font-size:12px;
    cursor:pointer; font-family:var(--cc-body); transition:background .15s, border-color .15s, color .15s; }
  #view-flow .cc-chip i { width:8px; height:8px; border-radius:50%; display:inline-block; opacity:.35; }
  #view-flow .cc-chip.on { color:var(--cc-text); border-color:var(--cc-muted-2); }
  #view-flow .cc-chip.on i { opacity:1; }
  #view-flow .cc-linkbtn { min-height:30px; background:none; border:none; color:var(--cc-cyan); font-size:11.5px; cursor:pointer;
    font-family:var(--cc-body); text-decoration:underline; text-underline-offset:2px; }
  #view-flow .cc-read { margin:0 0 24px; border:1px solid var(--cc-hair); border-radius:16px;
    background:linear-gradient(135deg, rgba(123,110,246,.07), rgba(34,211,238,.05)); padding:18px 22px;
    display:flex; gap:16px; align-items:flex-start; }
  #view-flow .cc-read-status { flex:0 0 auto; width:12px; height:12px; border-radius:50%; margin-top:6px;
    background:var(--cc-violet); box-shadow:0 0 0 4px rgba(123,110,246,.15); }
  #view-flow .cc-verdict { font-family:var(--cc-display); font-weight:600; font-size:17px; line-height:1.45; }
  #view-flow .cc-verdict b { color:var(--cc-green); }
  #view-flow .cc-sub { color:var(--cc-muted); font-size:13px; margin-top:6px; }
  #view-flow .cc-kpis { display:grid; grid-template-columns:repeat(5,1fr); gap:14px; margin-bottom:24px; }
  #view-flow .cc-kpi { background:var(--cc-panel); border:1px solid var(--cc-hair); border-radius:14px; padding:18px 18px 16px; position:relative; overflow:hidden; }
  #view-flow .cc-kpi-accent { position:absolute; left:0; top:0; bottom:0; width:3px; background:var(--cc-violet); }
  #view-flow .cc-kpi:nth-child(1) .cc-kpi-accent { background:var(--cc-text); }
  #view-flow .cc-kpi:nth-child(2) .cc-kpi-accent { background:var(--cc-cyan); }
  #view-flow .cc-kpi:nth-child(3) .cc-kpi-accent { background:var(--cc-amber); }
  #view-flow .cc-kpi:nth-child(4) .cc-kpi-accent { background:var(--cc-violet); }
  #view-flow .cc-kpi:nth-child(5) .cc-kpi-accent { background:var(--cc-green); }
  #view-flow .cc-num { font-family:var(--cc-display); font-weight:700; font-size:30px; line-height:1; }
  #view-flow .cc-lbl { color:var(--cc-muted); font-size:12px; margin-top:8px; text-transform:uppercase; letter-spacing:.5px; }
  #view-flow .cc-delta { font-family:var(--cc-mono); font-size:11px; margin-top:7px; color:var(--cc-muted); }
  #view-flow .cc-est { display:inline-flex; align-items:center; border:1px solid rgba(245,165,36,.42); color:var(--cc-amber);
    border-radius:999px; padding:1px 6px; font-family:var(--cc-mono); font-size:9px; text-transform:uppercase; margin-left:6px; }
  #view-flow .cc-grid { display:grid; grid-template-columns:repeat(12,1fr); gap:16px; }
  #view-flow .cc-panel { background:var(--cc-panel); border:1px solid var(--cc-hair); border-radius:16px; padding:20px 20px 18px; min-width:0; }
  #view-flow .cc-col-12 { grid-column:span 12; }
  #view-flow .cc-phead { display:flex; justify-content:space-between; align-items:flex-start; gap:10px; flex-wrap:wrap; }
  #view-flow .cc-panel h2 { font-family:var(--cc-display); font-weight:600; font-size:16px; margin:0; display:flex; align-items:center; gap:9px; letter-spacing:0; }
  #view-flow .cc-hint { color:var(--cc-muted-2); font-size:12px; margin-top:3px; margin-bottom:14px; }
  #view-flow .cc-note { font-size:10.5px; color:var(--cc-muted-2); font-family:var(--cc-mono); border:1px solid var(--cc-hair);
    border-radius:20px; padding:3px 9px; white-space:nowrap; }
  #view-flow .cc-chart-box { position:relative; height:300px; }
  #view-flow .cc-chart-box.tall { height:430px; }
  #view-flow .cc-chart-empty { display:flex; height:100%; align-items:center; justify-content:center; color:var(--cc-muted); font-size:12px; border:1px dashed var(--cc-hair); border-radius:10px; }
  #view-flow .cc-guide { font-size:11.5px; color:var(--cc-muted); background:rgba(40,50,76,.28); border-radius:9px; padding:9px 12px; margin-top:13px; line-height:1.55; }
  #view-flow .cc-guide .k { font-family:var(--cc-mono); font-size:9.5px; letter-spacing:.5px; text-transform:uppercase; color:var(--cc-muted-2); margin-right:3px; }
  #view-flow .cc-pipeline { overflow-x:auto; padding-bottom:6px; }
  #view-flow .cc-declined { display:inline-flex; align-items:center; gap:8px; font-size:12px; color:var(--cc-muted);
    background:var(--cc-panel-2); border:1px solid var(--cc-hair); border-radius:20px; padding:5px 12px; margin-bottom:12px; }
  #view-flow .cc-declined b { color:var(--cc-danger); font-family:var(--cc-mono); }
  #view-flow .cc-startbar { display:flex; align-items:flex-end; margin-bottom:2px; }
  #view-flow .cc-startslot { flex:1 1 0; min-width:190px; display:flex; flex-direction:column; align-items:center; }
  #view-flow .cc-hspacer { flex:0 0 44px; width:44px; }
  #view-flow .cc-startnode { background:var(--cc-green); color:#04231a; font-family:var(--cc-display); font-weight:700;
    font-size:12.5px; padding:8px 18px; border-radius:22px; box-shadow:0 4px 16px rgba(47,214,160,.35); }
  #view-flow .cc-startline { width:2px; height:16px; background:#6b78a0; }
  #view-flow .cc-flow { display:flex; gap:0; align-items:stretch; position:relative; }
  #view-flow .cc-flowsvg { position:absolute; inset:0; width:100%; height:100%; pointer-events:none; overflow:visible; z-index:0; }
  #view-flow .cc-phase { flex:1 1 0; min-width:190px; background:var(--cc-panel-2); border:1px solid var(--cc-hair);
    border-radius:13px; padding:12px; position:relative; z-index:1; }
  #view-flow .cc-phhead { display:flex; justify-content:space-between; align-items:center; margin-bottom:10px; padding-bottom:9px; border-bottom:1px solid var(--cc-hair); }
  #view-flow .cc-phname { font-family:var(--cc-display); font-weight:700; font-size:13px; letter-spacing:.3px; }
  #view-flow .cc-phtot { font-family:var(--cc-mono); font-weight:700; font-size:16px; }
  #view-flow .cc-pstage { width:100%; display:flex; justify-content:space-between; align-items:center; gap:8px; padding:9px 11px;
    border:1px solid var(--cc-hair); background:var(--cc-panel); border-radius:9px; font-size:12px; cursor:pointer;
    transition:background .15s, border-color .15s; color:var(--cc-text); font-family:var(--cc-body); text-align:left; min-height:40px; }
  #view-flow .cc-pstage:hover, #view-flow .cc-pstage:focus-visible { border-color:var(--cc-muted-2); background:rgba(40,50,76,.5); outline:none; }
  #view-flow .cc-pstage.zero { color:var(--cc-muted-2); }
  #view-flow .cc-pcount { font-family:var(--cc-mono); font-weight:700; background:var(--cc-panel); border:1px solid var(--cc-hair);
    border-radius:20px; min-width:26px; text-align:center; padding:1px 7px; font-size:11px; }
  #view-flow .cc-hconn { flex:0 0 44px; width:44px; }
  #view-flow .cc-vconn { display:flex; flex-direction:column; align-items:center; padding:2px 0; }
  #view-flow .cc-vconn .vline { width:2px; height:12px; background:#7d8ab0; }
  #view-flow .cc-vconn .vchev { width:0; height:0; border-left:5px solid transparent; border-right:5px solid transparent; border-top:8px solid #c9d2e3; }
  #view-flow .cc-tbl-wrap { overflow-x:auto; border-radius:10px; border:1px solid var(--cc-hair); }
  #view-flow table.cc-table { width:100%; border-collapse:collapse; font-size:12.5px; min-width:980px; }
  #view-flow .cc-table th { position:sticky; top:0; background:var(--cc-panel-2); text-align:left; padding:10px 12px;
    font-family:var(--cc-mono); font-size:10px; text-transform:uppercase; letter-spacing:.5px; color:var(--cc-muted);
    border-bottom:1px solid var(--cc-hair); white-space:nowrap; }
  #view-flow .cc-table td { padding:11px 12px; border-bottom:1px solid rgba(40,50,76,.5); white-space:nowrap; vertical-align:top; }
  #view-flow .cc-table tbody tr { cursor:pointer; transition:background .1s; }
  #view-flow .cc-table tbody tr:hover { background:rgba(40,50,76,.32); }
  #view-flow .cc-gid { font-family:var(--cc-mono); font-weight:700; color:var(--cc-violet); }
  #view-flow .cc-muted { color:var(--cc-muted-2); }
  #view-flow .cc-rankb { font-family:var(--cc-mono); font-weight:700; min-width:24px; height:24px; display:inline-flex;
    align-items:center; justify-content:center; border-radius:7px; background:var(--cc-panel-2); border:1px solid var(--cc-hair); padding:0 6px; }
  #view-flow .cc-rankb.r1 { color:var(--cc-danger); border-color:rgba(239,93,107,.4); }
  #view-flow .cc-rankb.r2 { color:var(--cc-amber); border-color:rgba(245,165,36,.4); }
  #view-flow .cc-rankb.r3 { color:var(--cc-cyan); border-color:rgba(34,211,238,.35); }
  #view-flow .cc-pill { font-size:11px; padding:3px 9px; border-radius:20px; border:1px solid var(--cc-hair); color:var(--cc-muted); display:inline-block; }
  #view-flow .cc-scrim { position:fixed; inset:0; background:rgba(5,8,15,.6); backdrop-filter:blur(2px); opacity:0; pointer-events:none; transition:.25s; z-index:940; }
  #view-flow .cc-scrim.open { opacity:1; pointer-events:auto; }
  #view-flow .cc-drawer { position:fixed; top:0; right:0; height:100%; width:min(720px,96vw); background:var(--cc-panel);
    border-left:1px solid var(--cc-hair); z-index:950; transform:translateX(100%); transition:transform .3s cubic-bezier(.4,0,.2,1);
    display:flex; flex-direction:column; box-shadow:-30px 0 60px rgba(0,0,0,.4); color:var(--cc-text); font-family:var(--cc-body); }
  #view-flow .cc-drawer.open { transform:translateX(0); }
  #view-flow .cc-dhead { padding:22px 24px 16px; border-bottom:1px solid var(--cc-hair); display:flex; justify-content:space-between; align-items:flex-start; gap:12px; }
  #view-flow .cc-eyebrow { font-family:var(--cc-mono); font-size:11px; color:var(--cc-muted); text-transform:uppercase; letter-spacing:.8px; }
  #view-flow .cc-dhead h3 { font-family:var(--cc-display); font-weight:600; font-size:20px; margin:5px 0 0; letter-spacing:0; }
  #view-flow .cc-subm { font-size:12px; color:var(--cc-muted); margin-top:5px; }
  #view-flow .cc-dclose { background:var(--cc-panel-2); border:1px solid var(--cc-hair); color:var(--cc-muted); width:34px; height:34px;
    border-radius:9px; cursor:pointer; font-size:17px; flex:0 0 auto; }
  #view-flow .cc-dclose:hover { color:var(--cc-text); border-color:var(--cc-muted); }
  #view-flow .cc-dbody { padding:22px 24px; overflow-y:auto; flex:1; }
  #view-flow .cc-dstats { display:grid; grid-template-columns:repeat(4,1fr); gap:10px; margin-bottom:8px; }
  #view-flow .cc-dstat { background:var(--cc-panel-2); border:1px solid var(--cc-hair); border-radius:11px; padding:12px; }
  #view-flow .cc-dstat .v { font-family:var(--cc-display); font-weight:700; font-size:17px; }
  #view-flow .cc-dstat .k { font-size:10px; color:var(--cc-muted); margin-top:4px; text-transform:uppercase; letter-spacing:.4px; }
  #view-flow .cc-dtitle { font-family:var(--cc-display); font-weight:600; font-size:13px; color:var(--cc-muted); text-transform:uppercase; letter-spacing:.6px; margin:22px 0 12px; display:flex; align-items:center; gap:8px; }
  #view-flow .cc-dtitle::after { content:''; flex:1; height:1px; background:var(--cc-hair); }
  #view-flow .cc-planbox { background:var(--cc-panel-2); border:1px solid var(--cc-hair); border-radius:11px; padding:14px 16px; display:grid; grid-template-columns:repeat(3,1fr); gap:12px 18px; }
  #view-flow .cc-plan .t { font-size:10.5px; color:var(--cc-muted); text-transform:uppercase; letter-spacing:.4px; }
  #view-flow .cc-plan .v { font-family:var(--cc-mono); font-weight:700; font-size:14px; margin-top:3px; }
  #view-flow .cc-gaxis { display:flex; justify-content:space-between; font-family:var(--cc-mono); font-size:10px; color:var(--cc-muted-2); margin:0 0 10px 188px; }
  #view-flow .cc-grow { display:grid; grid-template-columns:176px 1fr 48px; gap:12px; align-items:center; margin-bottom:7px; }
  #view-flow .cc-glabel { font-size:12px; line-height:1.25; text-align:right; color:var(--cc-muted); overflow:hidden; text-overflow:ellipsis; }
  #view-flow .cc-glabel.stage { font-family:var(--cc-display); font-weight:700; color:var(--cc-text); }
  #view-flow .cc-glabel.task { font-family:var(--cc-mono); font-size:11px; color:var(--cc-muted); padding-left:10px; }
  #view-flow .cc-gtrack { position:relative; height:16px; background:rgba(40,50,76,.28); border-radius:6px; }
  #view-flow .cc-gseg { position:absolute; top:2px; height:12px; border-radius:3px; min-width:2px; }
  #view-flow .cc-gseg.actual, #view-flow .cc-gseg.progress { background:var(--cc-blue); }
  #view-flow .cc-gseg.stage { background:rgba(75,139,245,.36); top:5px; height:6px; }
  #view-flow .cc-gseg.saved { background:var(--cc-green); }
  #view-flow .cc-gseg.overrun { background:var(--cc-amber); }
  #view-flow .cc-gseg.future { background:transparent; border:1px dashed var(--cc-muted-2); top:1px; height:14px; }
  #view-flow .cc-gdelta { font-family:var(--cc-mono); font-size:11px; text-align:right; color:var(--cc-muted-2); }
  #view-flow .cc-gdelta.saved, #view-flow .cc-gdelta.zero { color:var(--cc-green); font-weight:700; }
  #view-flow .cc-gdelta.overrun { color:var(--cc-danger); font-weight:700; }
  #view-flow .cc-glegend { display:flex; gap:16px; flex-wrap:wrap; margin-top:14px; font-size:11px; color:var(--cc-muted); }
  #view-flow .cc-glegend i { display:inline-block; width:12px; height:8px; border-radius:2px; margin-right:5px; vertical-align:middle; }
  #view-flow .cc-tl-loading, #view-flow .cc-tl-empty { min-height:118px; display:flex; align-items:center; justify-content:center; color:var(--cc-muted); border:1px dashed var(--cc-hair); border-radius:11px; font-size:12px; }
  #view-flow .cc-tl-spinner { width:22px; height:22px; border:2px solid var(--cc-hair); border-top-color:var(--cc-blue); border-radius:50%; animation:spin .75s linear infinite; margin-right:9px; }
  #view-flow .cc-action { display:inline-flex; min-height:36px; align-items:center; justify-content:center; border:1px solid var(--cc-hair);
    border-radius:9px; background:var(--cc-panel-2); color:var(--cc-text); padding:8px 12px; cursor:pointer; font:600 12px var(--cc-body);
    text-decoration:none; gap:8px; }
  #view-flow .cc-action.primary { background:var(--cc-violet); border-color:var(--cc-violet); color:#fff; }
  #view-flow .cc-stage-list { display:grid; gap:8px; }
  #view-flow .cc-stage-item { display:flex; justify-content:space-between; gap:12px; padding:10px 12px; background:var(--cc-panel-2);
    border:1px solid var(--cc-hair); border-radius:10px; cursor:pointer; }
  #view-flow .cc-stage-delta { font-family:var(--cc-mono); font-weight:700; }
  #view-flow .cc-stage-delta.over { color:var(--cc-danger); }
  #view-flow .cc-stage-delta.under, #view-flow .cc-stage-delta.zero { color:var(--cc-green); }
  #view-flow .cc-foot { margin-top:26px; border:1px solid var(--cc-hair); border-radius:12px; padding:14px 18px; background:var(--cc-panel);
    color:var(--cc-muted); font-size:12px; line-height:1.6; }
  #view-flow .cc-foot b { color:var(--cc-text); }
  #view-flow .cc-foot code { font-family:var(--cc-mono); color:var(--cc-text); font-size:11px; }
  @media(max-width:1040px){
    #view-flow .cc-kpis { grid-template-columns:repeat(2,1fr); }
    #view-flow .cc-dstats, #view-flow .cc-planbox { grid-template-columns:repeat(2,1fr); }
  }
  @media(max-width:680px){
    #view-flow .cc-wrap { padding:18px 14px 84px; }
    #view-flow .cc-kpis { grid-template-columns:1fr; }
    #view-flow .cc-fdiv { display:none; }
    #view-flow .cc-dstats, #view-flow .cc-planbox { grid-template-columns:1fr; }
    #view-flow .cc-gaxis { margin-left:112px; }
    #view-flow .cc-grow { grid-template-columns:100px 1fr 42px; gap:8px; }
    #view-flow .cc-chart-box, #view-flow .cc-chart-box.tall { height:300px; }
  }
  @media(prefers-reduced-motion:reduce){
    #view-flow *, #view-flow .cc-drawer, #view-flow .cc-scrim { transition:none!important; }
  }
"""

CC_HTML = r"""
<section class="cc-wrap" aria-label="Game Pipeline Control Center">
  <div class="cc-topline">
    <div><h1>Game Pipeline Control Center<span class="cc-dot">.</span></h1></div>
    <div class="cc-gen">PRODUCTION PIPELINE &middot; as of {{AS_OF}} &middot; DURATIONS IN DAYS</div>
  </div>

  <div class="cc-filters" id="cc-filters">
    <div class="cc-fgroup"><span class="cc-flabel">Rank</span><div id="cc-rankChips" style="display:flex;gap:6px;flex-wrap:wrap"></div></div>
    <div class="cc-fdiv"></div>
    <div class="cc-fgroup"><span class="cc-flabel">Category</span><div id="cc-catChips" style="display:flex;gap:6px;flex-wrap:wrap"></div></div>
    <div class="cc-fdiv"></div>
    <div class="cc-fgroup"><span class="cc-flabel">Type</span><div id="cc-typeChips" style="display:flex;gap:6px;flex-wrap:wrap"></div></div>
    <div class="cc-fdiv"></div>
    <div class="cc-fgroup"><span class="cc-flabel">Studio</span><div id="cc-studioChips" style="display:flex;gap:6px;flex-wrap:wrap"></div><button class="cc-linkbtn" id="cc-resetFilters">reset</button></div>
  </div>

  <div class="cc-read">
    <div class="cc-read-status"></div>
    <div>
      <div class="cc-verdict" id="cc-verdict">Loading pipeline status...</div>
      <div class="cc-sub">Pipeline shows Ideas, Games, Certification, and Release. Localization is excluded from this flow view; open a game for the existing field-driven timeline.</div>
    </div>
  </div>

  <div class="cc-kpis">
    <div class="cc-kpi"><span class="cc-kpi-accent"></span><div class="cc-num" id="cc-kProd">-</div><div class="cc-lbl">Games in production</div><div class="cc-delta" id="cc-kProdSub">-</div></div>
    <div class="cc-kpi"><span class="cc-kpi-accent"></span><div class="cc-num" id="cc-kDev">-</div><div class="cc-lbl">In development</div><div class="cc-delta">largest GAME stage</div></div>
    <div class="cc-kpi"><span class="cc-kpi-accent"></span><div class="cc-num" id="cc-kCert">-</div><div class="cc-lbl">In certification</div><div class="cc-delta" id="cc-kCertSub">-</div></div>
    <div class="cc-kpi"><span class="cc-kpi-accent"></span><div class="cc-num" id="cc-kAvg">-</div><div class="cc-lbl">Avg cycle<span class="cc-est">proxy</span></div><div class="cc-delta">created to updated</div></div>
    <div class="cc-kpi"><span class="cc-kpi-accent"></span><div class="cc-num" id="cc-kOnTime">-</div><div class="cc-lbl">Met benchmark<span class="cc-est">proxy</span></div><div class="cc-delta">relative to local average</div></div>
  </div>

  <div class="cc-grid">
    <div class="cc-panel cc-col-12">
      <div class="cc-phead"><div><h2>Production flow</h2><div class="cc-hint">Click a stage to inspect the games currently sitting there.</div></div><span class="cc-note">click a stage</span></div>
      <div class="cc-declined">Declined <b id="cc-declCount">0</b> rejected ideas</div>
      <div class="cc-pipeline" id="cc-flow"></div>
    </div>

    <div class="cc-panel cc-col-12">
      <div class="cc-phead"><div><h2>On-benchmark vs over-benchmark, by month <span class="cc-est">proxy</span></h2><div class="cc-hint" id="cc-tlHint"></div></div><span class="cc-note">created-to-updated cycle</span></div>
      <div class="cc-chart-box"><canvas id="cc-tlChart"></canvas></div>
      <div class="cc-guide"><span class="k">Read</span> Bars show games above their category/type proxy benchmark in each month; the line shows average cycle as percent of benchmark.</div>
    </div>

    <div class="cc-panel cc-col-12">
      <div class="cc-phead"><div><h2>Games by studio and type</h2><div class="cc-hint" id="cc-spdHint"></div></div></div>
      <div class="cc-chart-box tall"><canvas id="cc-lateChart"></canvas></div>
      <div class="cc-guide" id="cc-spdGuide"></div>
    </div>

    <div class="cc-panel cc-col-12">
      <div class="cc-phead"><div><h2>Games in progress</h2><div class="cc-hint">Click a row for details, Jira link, and the real timeline modal.</div></div><span id="cc-tblCount" class="cc-note"></span></div>
      <div class="cc-tbl-wrap">
        <table class="cc-table"><thead><tr>
          <th>ID</th><th>Summary</th><th>Category</th><th>Type</th><th>Rank</th><th>Studio</th><th>Market</th><th>Batch</th><th>Status</th><th>Duration <span class="cc-est">proxy</span></th><th>Create</th><th>Wishful</th><th>Last update</th>
        </tr></thead><tbody id="cc-tblBody"></tbody></table>
      </div>
    </div>
  </div>

  <div class="cc-foot">
    <b>Data notes.</b> Rank is read from the exported Jira data when available. Duration and benchmark panels are labeled proxy because they use created-to-updated cycle time, while the per-game stage timeline uses the existing real Jira timeline endpoint.
  </div>
</section>

<div class="cc-scrim" id="cc-scrim"></div>
<aside class="cc-drawer" id="cc-drawer" role="dialog" aria-modal="true" aria-labelledby="cc-dTitle">
  <div class="cc-dhead">
    <div><div class="cc-eyebrow" id="cc-dEyebrow">Game</div><h3 id="cc-dTitle">-</h3><div class="cc-subm" id="cc-dSub"></div></div>
    <button class="cc-dclose" id="cc-dClose" aria-label="Close">&times;</button>
  </div>
  <div class="cc-dbody" id="cc-dBody"></div>
</aside>
"""

CC_JS = r"""
(function(){
  const root = document.getElementById('view-flow');
  if(!root || typeof DATA === 'undefined') return;

  const spaceOrder = ['IDEAS','GAMES','CERTIFICATION','RELEASE'];
  const spaceColor = {IDEAS:'#7b6ef6', GAMES:'#22d3ee', CERTIFICATION:'#f5a524', RELEASE:'#2fd6a0'};
  const palette = ['#22d3ee','#7b6ef6','#2fd6a0','#f5a524','#ef5d6b','#a78bfa','#38bdf8','#fb7185'];
  const typeOrder = ['New Game','Reskin Game','Change Game'];
  const priorityRank = {Highest:1, High:2, Medium:5, Low:8, Lowest:10};
  let FLOW = [], TICKETS = [], GAMES = [], HISTORY = [], BENCH = {}, MONTHS = [], MONTHKEYS = [];
  let charts = {tl:null, studio:null};
  const F = {ranks:new Set(), cats:new Set(), types:new Set(), studios:new Set()};

  function $(id){ return document.getElementById(id); }
  function uniq(arr){ return [...new Set(arr.filter(Boolean))].sort((a,b)=>String(a).localeCompare(String(b))); }
  function mean(a){ return a.length ? a.reduce((x,y)=>x+y,0)/a.length : 0; }
  function dateOnly(s){ return s ? String(s).slice(0,10) : ''; }
  function daysBetween(a,b){
    const da = dateOnly(a), db = dateOnly(b);
    if(!da) return 0;
    const end = db ? new Date(db) : new Date();
    return Math.max(1, Math.round((end - new Date(da)) / 864e5));
  }
  function parseRank(raw, priority){
    const s = String(raw == null ? '' : raw).trim();
    if(s){
      const n = Number(s.replace(/[^\d.-]/g,''));
      if(Number.isFinite(n)) return n;
    }
    return priorityRank[priority] || 99;
  }
  function displayRank(raw){
    const s = String(raw == null ? '' : raw).trim();
    if(!s) return '—';
    const n = Number(s.replace(/[^\d.-]/g,''));
    return Number.isFinite(n) ? String(n) : s;
  }
  function rankClass(rank){
    if(rank <= 2) return 'r1';
    if(rank <= 5) return 'r2';
    if(rank < 99) return 'r3';
    return '';
  }
  function monthIndex(dstr){
    if(!dstr) return 0;
    const d = new Date(dstr);
    for(let i=0;i<MONTHKEYS.length;i++){
      if(d.getFullYear()===MONTHKEYS[i].y && d.getMonth()===MONTHKEYS[i].m) return i;
    }
    return d < new Date(MONTHKEYS[0].y, MONTHKEYS[0].m, 1) ? 0 : MONTHKEYS.length - 1;
  }
  function benchmark(cat,type){
    if(BENCH[cat] && BENCH[cat][type]) return BENCH[cat][type];
    const catRows = HISTORY.filter(h => h.cat === cat).map(h => h.duration);
    if(catRows.length) return Math.round(mean(catRows));
    return HISTORY.length ? Math.round(mean(HISTORY.map(h => h.duration))) : 1;
  }
  function filteredTickets(){
    return TICKETS.filter(t =>
      (!F.ranks.size || F.ranks.has(String(t.rankDisplay))) &&
      (!F.cats.size || F.cats.has(t.cat)) &&
      (!F.types.size || F.types.has(t.type)) &&
      (!F.studios.size || F.studios.has(t.studio))
    );
  }
  function filteredGames(){
    return filteredTickets().filter(t => t.space === 'GAMES');
  }

  function loadData(){
    const meta = DATA.meta || {}, tickets = DATA.tickets || {};
    const now = new Date();
    MONTHKEYS = [];
    for(let i=5;i>=0;i--){
      const d = new Date(now.getFullYear(), now.getMonth()-i, 1);
      MONTHKEYS.push({y:d.getFullYear(), m:d.getMonth(), label:d.toLocaleString('en-US',{month:'short'})});
    }
    MONTHS = MONTHKEYS.map(k => k.label);

    const bySpace = {};
    Object.entries(meta).forEach(([id,m]) => {
      if(id === 'declined') return;
      if(m.space === 'LOCALIZATION') return;
      (bySpace[m.space] = bySpace[m.space] || []).push({id, title:m.title, count:m.count || 0, spaceKey:m.space_key});
    });
    FLOW = spaceOrder.filter(sp => bySpace[sp]).map(sp => ({
      key:sp, color:spaceColor[sp] || '#7b6ef6',
      stages:bySpace[sp],
      total:bySpace[sp].reduce((a,x)=>a + (x.count || 0), 0)
    }));

    TICKETS = [];
    Object.entries(tickets).forEach(([stageId, list]) => {
      const sm = meta[stageId] || {title:stageId, space:'', space_key:''};
      (list || []).forEach(t => {
        const rank = parseRank(t.rank, t.priority);
        const rankText = displayRank(t.rank);
        const duration = daysBetween(t.created, t.updated);
        TICKETS.push({
          id:t.key, name:t.summary || t.key, cat:t.game_category || 'Unspecified', type:t.game_type || 'Unspecified',
          rank, rankDisplay:rankText, studio:t.game_studio || 'Unspecified', market:t.market || '-',
          batch:t.batch || '-', status:sm.title, space:sm.space, spaceKey:sm.space_key,
          wishful:t.wishful_date || '-', create:dateOnly(t.created), lastUpdate:dateOnly(t.updated),
          url:t.url || '', duration, month:monthIndex(t.created || t.updated), priority:t.priority || '',
          stageId, assignee:t.assignee || 'Unassigned'
        });
      });
    });
    GAMES = TICKETS.filter(t => t.space === 'GAMES');
    HISTORY = TICKETS.filter(t => t.cat && t.type && t.studio).map(t => ({
      cat:t.cat, type:t.type, studio:t.studio, duration:t.duration, month:t.month
    }));
    const cats = uniq(HISTORY.map(h => h.cat));
    BENCH = {};
    cats.forEach(cat => {
      BENCH[cat] = {};
      typeOrder.forEach(type => {
        const rows = HISTORY.filter(h => h.cat === cat && h.type === type).map(h => h.duration);
        BENCH[cat][type] = rows.length ? Math.round(mean(rows)) : null;
      });
    });
  }

  function chipHtml(value, color){
    return '<button class="cc-chip on" type="button" data-value="'+esc(value)+'"><i style="background:'+color+'"></i>'+esc(value)+'</button>';
  }
  function buildChipGroup(hostId, values, filterSet, colors){
    const host = $(hostId);
    if(!host) return;
    if(!values.length){
      host.innerHTML = '<span class="cc-muted" style="font-size:12px">No data</span>';
      return;
    }
    values.forEach(v => filterSet.add(String(v)));
    host.innerHTML = values.map((v,i) => chipHtml(String(v), colors ? colors[i % colors.length] : palette[i % palette.length])).join('');
    const syncOn = () => host.querySelectorAll('.cc-chip').forEach(b => b.classList.toggle('on', filterSet.has(b.dataset.value)));
    host.querySelectorAll('.cc-chip').forEach(btn => {
      let timer = null;
      // Single-click = toggle in/out (debounced 200ms so a double-click can pre-empt it).
      btn.addEventListener('click', () => {
        if(timer) return;
        timer = setTimeout(() => {
          timer = null;
          const v = btn.dataset.value;
          if(filterSet.has(v)) filterSet.delete(v); else filterSet.add(v);
          btn.classList.toggle('on', filterSet.has(v));
          renderAll();
        }, 200);
      });
      // Double-click = solo this value (only this chip on, all others off).
      btn.addEventListener('dblclick', () => {
        clearTimeout(timer); timer = null;
        filterSet.clear();
        filterSet.add(btn.dataset.value);
        syncOn();
        renderAll();
      });
    });
  }
  function buildFilters(){
    const ranks = uniq(TICKETS.map(t => t.rankDisplay)).sort((a,b)=>{
      if(a === '—') return 1;
      if(b === '—') return -1;
      return Number(a) - Number(b);
    });
    buildChipGroup('cc-rankChips', ranks, F.ranks, ['#ef5d6b','#f5a524','#22d3ee','#7b6ef6']);
    buildChipGroup('cc-catChips', uniq(TICKETS.map(t => t.cat)), F.cats);
    buildChipGroup('cc-typeChips', uniq(TICKETS.map(t => t.type)), F.types, ['#22d3ee','#7b6ef6','#2fd6a0']);
    buildChipGroup('cc-studioChips', uniq(TICKETS.map(t => t.studio)), F.studios);
    const reset = $('cc-resetFilters');
    if(reset) reset.addEventListener('click', () => {
      Object.values(F).forEach(s => s.clear());
      root.querySelectorAll('.cc-chip').forEach(btn => {
        btn.classList.add('on');
        const group = btn.closest('[id]');
        if(group && group.id === 'cc-rankChips') F.ranks.add(btn.dataset.value);
        if(group && group.id === 'cc-catChips') F.cats.add(btn.dataset.value);
        if(group && group.id === 'cc-typeChips') F.types.add(btn.dataset.value);
        if(group && group.id === 'cc-studioChips') F.studios.add(btn.dataset.value);
      });
      renderAll();
    });
  }

  function renderKPIs(rows){
    const games = rows.filter(t => t.space === 'GAMES');
    const cert = rows.filter(t => t.space === 'CERTIFICATION');
    const ideas = rows.filter(t => t.space === 'IDEAS');
    const dev = games.filter(t => t.status === 'Development').length;
    const certInProgress = cert.filter(t => t.status !== 'Done').length;
    const avg = games.length ? Math.round(mean(games.map(t => t.duration))) : 0;
    const comparable = games.filter(t => t.cat && t.type);
    const met = comparable.length ? Math.round(100 * comparable.filter(t => t.duration <= benchmark(t.cat,t.type)).length / comparable.length) : 0;
    $('cc-kProd').textContent = games.length;
    $('cc-kProdSub').textContent = 'Ideas ' + ideas.length + ' - Cert ' + cert.length;
    $('cc-kDev').textContent = dev;
    $('cc-kCert').textContent = cert.length;
    $('cc-kCertSub').textContent = certInProgress + ' active - ' + (cert.length - certInProgress) + ' done';
    $('cc-kAvg').textContent = avg ? avg + 'd' : '-';
    $('cc-kOnTime').textContent = comparable.length ? met + '%' : '-';
    $('cc-verdict').innerHTML = esc(games.length) + ' games in production, ' + esc(cert.length) + ' in certification, <b>' + esc(dev) + ' in Development</b>. Benchmarks are proxy cycle-time and timelines remain Jira field-driven.';
  }

  function currentStageCounts(rows){
    const counts = {};
    rows.forEach(t => { counts[t.stageId] = (counts[t.stageId] || 0) + 1; });
    return counts;
  }
  function renderFlow(rows){
    const host = $('cc-flow');
    if(!host) return;
    const counts = currentStageCounts(rows);
    const declined = DATA.meta && DATA.meta.declined ? DATA.meta.declined.count || 0 : 0;
    $('cc-declCount').textContent = declined;

    let sb = '<div class="cc-startbar">';
    FLOW.forEach((p,i) => {
      sb += '<div class="cc-startslot">'+(i===0?'<div class="cc-startnode">Start</div><span class="cc-startline"></span>':'')+'</div>';
      if(i < FLOW.length - 1) sb += '<div class="cc-hspacer"></div>';
    });
    sb += '</div>';

    let html = '<div class="cc-flow"><svg class="cc-flowsvg" id="cc-flowsvg"></svg>';
    FLOW.forEach((phase, i) => {
      const total = phase.stages.reduce((a,s) => a + (counts[s.id] || 0), 0);
      const stages = phase.stages.map((s,j) => {
        const c = counts[s.id] || 0;
        return (j>0?'<div class="cc-vconn"><span class="vline"></span><span class="vchev"></span></div>':'')+
          '<button class="cc-pstage '+(c===0?'zero':'')+'" type="button" data-stage-id="'+esc(s.id)+'" title="'+esc(s.title)+'">'+
          '<span>'+esc(s.title)+'</span><span class="cc-pcount">'+c+'</span></button>';
      }).join('');
      html += '<div class="cc-phase"><div class="cc-phhead"><span class="cc-phname" style="color:'+phase.color+'">'+esc(phase.key)+'</span><span class="cc-phtot">'+total+'</span></div>'+stages+'</div>';
      if(i < FLOW.length - 1) html += '<div class="cc-hconn"></div>';
    });
    html += '</div>';
    host.innerHTML = sb + html;
    host.querySelectorAll('[data-stage-id]').forEach(btn => btn.addEventListener('click', () => openStageDrawer(btn.dataset.stageId)));
    requestAnimationFrame(drawConnectors);
  }
  function drawConnectors(){
    const flow = root.querySelector('.cc-flow'), svg = $('cc-flowsvg');
    if(!flow || !svg || !flow.clientWidth) return;
    svg.setAttribute('viewBox','0 0 '+flow.clientWidth+' '+flow.clientHeight);
    svg.setAttribute('width', flow.clientWidth);
    svg.setAttribute('height', flow.clientHeight);
    const fr = flow.getBoundingClientRect();
    const phases = [...flow.querySelectorAll('.cc-phase')];
    let paths = '';
    for(let i=0;i<phases.length-1;i++){
      const a = phases[i].querySelectorAll('.cc-pstage');
      const b = phases[i+1].querySelectorAll('.cc-pstage');
      if(!a.length || !b.length) continue;
      const last = a[a.length-1].getBoundingClientRect(), first = b[0].getBoundingClientRect();
      const x1 = last.right - fr.left, y1 = last.top - fr.top + last.height / 2;
      const x2 = first.left - fr.left, y2 = first.top - fr.top + first.height / 2;
      const mx = x1 + (x2 - x1) / 2;
      paths += '<path d="M '+x1+' '+y1+' H '+mx+' V '+y2+' H '+x2+'" fill="none" stroke="#94a3b8" stroke-width="2" marker-end="url(#ccah)"/>';
    }
    svg.innerHTML = '<defs><marker id="ccah" markerWidth="9" markerHeight="9" refX="7" refY="3" orient="auto"><path d="M0,0 L8,3 L0,6 Z" fill="#c9d2e3"/></marker></defs>'+paths;
  }

  function renderTable(rows){
    const games = rows.filter(t => t.space === 'GAMES').sort((a,b) => (a.rank - b.rank) || String(b.lastUpdate).localeCompare(String(a.lastUpdate)));
    $('cc-tblCount').textContent = games.length + ' games';
    const body = $('cc-tblBody');
    if(!body) return;
    body.innerHTML = games.map(t => (
      '<tr data-game-id="'+esc(t.id)+'">'+
      '<td><span class="cc-gid">'+esc(t.id)+'</span></td>'+
      '<td style="white-space:normal;min-width:220px">'+esc(t.name)+'</td>'+
      '<td>'+esc(t.cat || '-')+'</td>'+
      '<td>'+esc(t.type || '-')+'</td>'+
      '<td><span class="cc-rankb '+rankClass(t.rank)+'">'+esc(t.rankDisplay)+'</span></td>'+
      '<td>'+esc(t.studio || '-')+'</td>'+
      '<td>'+esc(t.market || '-')+'</td>'+
      '<td>'+esc(t.batch || '-')+'</td>'+
      '<td><span class="cc-pill">'+esc(t.status || '-')+'</span></td>'+
      '<td>'+t.duration+'d</td>'+
      '<td>'+esc(t.create || '-')+'</td>'+
      '<td>'+esc(t.wishful || '-')+'</td>'+
      '<td>'+esc(t.lastUpdate || '-')+'</td>'+
      '</tr>'
    )).join('') || '<tr><td colspan="13" class="cc-muted" style="text-align:center;padding:24px">No games match the selected filters.</td></tr>';
    body.querySelectorAll('[data-game-id]').forEach(row => row.addEventListener('click', () => openGameDrawer(row.dataset.gameId)));
  }

  function renderCharts(rows){
    const games = rows.filter(t => t.space === 'GAMES');
    const chartReady = !!window.Chart;
    if(!chartReady){
      root.querySelectorAll('.cc-chart-box').forEach(box => box.innerHTML = '<div class="cc-chart-empty">Chart.js is not available in this build.</div>');
      return;
    }
    if(charts.tl) charts.tl.destroy();
    if(charts.studio) charts.studio.destroy();

    const monthlyOver = MONTHS.map((_,i) => games.filter(g => g.cat && g.type && g.month === i && g.duration > benchmark(g.cat,g.type)).length);
    const monthlyRatio = MONTHS.map((_,i) => {
      const a = games.filter(g => g.cat && g.type && g.month === i).map(g => Math.round(100 * g.duration / benchmark(g.cat,g.type)));
      return a.length ? Math.round(mean(a)) : null;
    });
    const tlCtx = $('cc-tlChart');
    charts.tl = new Chart(tlCtx, {
      data:{labels:MONTHS,datasets:[
        {type:'bar', label:'Over benchmark', data:monthlyOver, backgroundColor:'rgba(239,93,107,.75)', borderRadius:6, yAxisID:'y'},
        {type:'line', label:'Avg cycle %', data:monthlyRatio, borderColor:'#22d3ee', backgroundColor:'#22d3ee', tension:.35, spanGaps:true, yAxisID:'y1'}
      ]},
      options:chartOptions({yTitle:'Games', y1Title:'% of benchmark'})
    });
    $('cc-tlHint').textContent = games.length + ' GAME tickets in the current filter.';

    const studios = uniq(games.map(g => g.studio)).slice(0, 14);
    const types = uniq(games.map(g => g.type)).filter(Boolean);
    const ds = (types.length ? types : ['Unspecified']).map((type,i) => ({
      label:type, data:studios.map(st => games.filter(g => g.studio === st && (g.type || 'Unspecified') === type).length),
      backgroundColor:palette[i % palette.length], borderRadius:6
    }));
    charts.studio = new Chart($('cc-lateChart'), {
      type:'bar',
      data:{labels:studios.length ? studios : ['No studio'], datasets:ds},
      options:chartOptions({stacked:true, indexAxis:'y', yTitle:'Studio', xTitle:'Games'})
    });
    $('cc-spdHint').textContent = studios.length + ' studios represented in the current filter.';
    $('cc-spdGuide').innerHTML = '<span class="k">Read</span> Counts are grouped by current GAME tickets, not completed historical throughput.';
  }
  function chartOptions(extra){
    const grid = 'rgba(139,149,173,.16)';
    const ticks = '#8b95ad';
    const opts = {
      responsive:true, maintainAspectRatio:false,
      plugins:{legend:{labels:{color:ticks, boxWidth:10, usePointStyle:true}}, tooltip:{mode:'index', intersect:false}},
      scales:{
        x:{stacked:!!extra.stacked, grid:{color:grid}, ticks:{color:ticks}},
        y:{stacked:!!extra.stacked, grid:{color:grid}, ticks:{color:ticks}, beginAtZero:true, title:{display:!!extra.yTitle, text:extra.yTitle, color:ticks}}
      }
    };
    if(extra.indexAxis) opts.indexAxis = extra.indexAxis;
    if(extra.xTitle) opts.scales.x.title = {display:true, text:extra.xTitle, color:ticks};
    if(extra.y1Title) opts.scales.y1 = {position:'right', grid:{drawOnChartArea:false}, ticks:{color:ticks}, beginAtZero:true, title:{display:true, text:extra.y1Title, color:ticks}};
    return opts;
  }

  function openDrawer(kind, title, subtitle, body){
    $('cc-dEyebrow').textContent = kind;
    $('cc-dTitle').textContent = title;
    $('cc-dSub').textContent = subtitle || '';
    $('cc-dBody').innerHTML = body;
    $('cc-scrim').classList.add('open');
    $('cc-drawer').classList.add('open');
  }
  function closeDrawer(){
    $('cc-scrim').classList.remove('open');
    $('cc-drawer').classList.remove('open');
  }
  function openTimelineFor(key){
    const game = TICKETS.find(t => t.id === key);
    if(window.openTimelineModal && game){
      window.openTimelineModal(key, {
        summary:game.name, studio:game.studio, market:game.market, batch:game.batch,
        category:game.cat, wishful:game.wishful, status:game.status, created:game.create
      });
    }
  }
  const timelineNames = ['Math','Contract Alignment','Development','Integration QC','Optimization','Packaging'];
  const timelineDurations = {'Math':5, 'Contract Alignment':3, 'Development':20, 'Integration QC':10, 'Optimization':5, 'Packaging':4};
  const timelineMonths = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  function tlDate(v){ return v ? new Date(String(v).substring(0, 10)) : null; }
  function tlDiff(a,b){ return Math.round((b - a) / 86400000); }
  function tlFmt(d){ return d ? String(d.getMonth()+1).padStart(2,'0') + '-' + String(d.getDate()).padStart(2,'0') : ''; }
  function tlDay(d){ return d ? timelineMonths[d.getMonth()] + ' ' + d.getDate() : '—'; }
  function estimateTimeline(created){
    let cur = tlDate(created) || new Date();
    cur = new Date(cur);
    return timelineNames.map(name => {
      const dur = timelineDurations[name] || 5;
      const end = new Date(cur);
      end.setDate(end.getDate() + dur - 1);
      const row = {name, level:0, actual_start:null, actual_end:null, eta:end.toISOString()};
      cur = new Date(end);
      cur.setDate(cur.getDate() + 1);
      return row;
    });
  }
  function timelineDelta(as_, ae, eta){
    if(as_ && ae && eta){
      const d = tlDiff(eta, ae);
      if(d > 0) return {text:'+' + d + 'd', cls:'overrun'};
      if(d < 0) return {text:d + 'd', cls:'saved'};
      return {text:'±0d', cls:'zero'};
    }
    if(as_ && ae) return {text:'±0d', cls:'zero'};
    if(as_) return {text:'active', cls:'progress'};
    return {text:'—', cls:'progress'};
  }
  function timelineMarkup(stages, estimated){
    stages = stages || [];
    const today = new Date();
    const dates = [today];
    stages.forEach(s => [s.actual_start, s.actual_end, s.eta].forEach(v => { const d = tlDate(v); if(d) dates.push(d); }));
    const minD = new Date(Math.min(...dates.map(d => d.getTime())));
    const maxD = new Date(Math.max(...dates.map(d => d.getTime())));
    const span = tlDiff(minD, maxD) || 1;
    const pct = d => (tlDiff(minD, d) / span * 100);
    const mid = new Date((minD.getTime() + maxD.getTime()) / 2);
    const seg = (cls, a, b, isStage) => '<span class="cc-gseg '+cls+(isStage && cls === 'actual' ? ' stage' : '')+'" style="left:'+Math.max(0, pct(a)).toFixed(1)+'%;width:'+Math.max(pct(b)-pct(a), .8).toFixed(1)+'%"></span>';
    const rows = stages.map(s => {
      const as_ = tlDate(s.actual_start), ae = tlDate(s.actual_end), eta = tlDate(s.eta);
      let segs = '';
      if(as_ && ae){
        const end = eta && eta < ae ? eta : ae;
        segs += seg('actual', as_, end, (s.level || 0) === 0);
        if(eta && ae < eta) segs += seg('saved', ae, eta, false);
        if(eta && ae > eta) segs += seg('overrun', eta, ae, false);
      } else if(as_) {
        segs += seg('progress', as_, today, false);
      } else {
        segs += '<span class="cc-gseg future" style="left:0;width:100%"></span>';
      }
      const delta = timelineDelta(as_, ae, eta);
      const labelCls = (s.level || 0) === 0 ? 'stage' : 'task';
      const label = s.name;
      return '<div class="cc-grow">'+
        '<div class="cc-glabel '+labelCls+'" title="'+esc(s.name)+'">'+esc(label)+'</div>'+
        '<div class="cc-gtrack" title="'+esc(s.name)+' · Start '+tlDay(as_)+' · End '+tlDay(ae)+' · Due '+tlDay(eta)+'">'+segs+'</div>'+
        '<div class="cc-gdelta '+delta.cls+'">'+esc(delta.text)+'</div>'+
      '</div>';
    }).join('');
    return (estimated ? '<div class="cc-note" style="display:inline-flex;margin-bottom:10px">estimated</div>' : '')+
      '<div class="cc-gaxis"><span>'+tlFmt(minD)+'</span><span>'+tlFmt(mid)+'</span><span>'+tlFmt(maxD)+'</span></div>'+
      rows+
      '<div class="cc-glegend"><span><i style="background:var(--cc-blue)"></i>Actual duration</span><span><i style="background:var(--cc-green)"></i>Time saved</span><span><i style="background:var(--cc-amber)"></i>Overrun past ETA</span><span><i style="border:1px dashed var(--cc-muted-2)"></i>Not started</span></div>';
  }
  async function renderGameTimeline(game){
    const host = $('cc-gameTimeline');
    const title = $('cc-gameTimelineTitle');
    if(!host) return;
    if(!String(game.id).startsWith('GAME-') && !String(game.id).startsWith('CER-') && !String(game.id).startsWith('LOC-')){
      if(title) title.textContent = 'Stage timeline (estimated)';
      host.innerHTML = timelineMarkup(estimateTimeline(game.create), true);
      return;
    }
    try {
      const resp = await fetch('/api/ticket/' + encodeURIComponent(game.id) + '/timeline');
      if(resp.ok){
        const data = await resp.json();
        const stages = data.stages || [];
        if(stages.length){
          if(title) title.textContent = data.estimated ? 'Stage timeline (estimated)' : 'Stage timeline';
          host.innerHTML = timelineMarkup(data.estimated ? estimateTimeline(game.create) : stages, !!data.estimated);
          return;
        }
      }
    } catch(e) {}
    if(title) title.textContent = 'Stage timeline (estimated)';
    host.innerHTML = timelineMarkup(estimateTimeline(game.create), true);
  }
  function openGameDrawer(key){
    const game = TICKETS.find(t => t.id === key);
    if(!game) return;
    const bm = game.cat && game.type ? benchmark(game.cat, game.type) : 0;
    const delta = bm ? game.duration - bm : 0;
    const body =
      '<div class="cc-dstats">'+
      '<div class="cc-dstat"><div class="v">'+esc(game.duration)+'d</div><div class="k">proxy duration</div></div>'+
      '<div class="cc-dstat"><div class="v">'+(bm ? esc(bm)+'d' : '-')+'</div><div class="k">proxy benchmark</div></div>'+
      '<div class="cc-dstat"><div class="v">'+(bm ? (delta>0?'+':'')+esc(delta)+'d' : '-')+'</div><div class="k">delta</div></div>'+
      '<div class="cc-dstat"><div class="v">'+esc(game.rankDisplay)+'</div><div class="k">rank</div></div>'+
      '</div>'+
      '<div class="cc-dtitle">Plan fields</div>'+
      '<div class="cc-planbox">'+
      planItem('Category', game.cat || '-') + planItem('Type', game.type || '-') + planItem('Studio', game.studio || '-')+
      planItem('Market', game.market || '-') + planItem('Batch', game.batch || '-') + planItem('Wishful', game.wishful || '-')+
      '</div>'+
      '<div class="cc-dtitle" id="cc-gameTimelineTitle">Stage timeline</div>'+
      '<div id="cc-gameTimeline" class="cc-game-timeline"><div class="cc-tl-loading"><span class="cc-tl-spinner"></span>Loading timeline...</div></div>';
    openDrawer('Game', game.id + ' - ' + game.name, game.status + ' - ' + (game.assignee || 'Unassigned'), body);
    renderGameTimeline(game);
  }
  function openStageDrawer(stageId){
    const meta = DATA.meta && DATA.meta[stageId] ? DATA.meta[stageId] : {title:stageId, space:''};
    const rows = filteredTickets().filter(t => t.stageId === stageId).sort((a,b) => (a.rank - b.rank) || String(b.lastUpdate).localeCompare(String(a.lastUpdate)));
    const tableRows = rows.map(t => {
      const bm = t.cat && t.type ? benchmark(t.cat, t.type) : 0;
      const delta = bm ? t.duration - bm : null;
      const deltaText = delta == null ? '-' : (delta > 0 ? '+' : '') + delta + 'd';
      const deltaCls = delta == null ? '' : (delta > 0 ? 'over' : (delta < 0 ? 'under' : 'zero'));
      return '<tr data-game-id="'+esc(t.id)+'">'+
        '<td><span class="cc-gid">'+esc(t.id)+'</span></td>'+
        '<td style="white-space:normal;min-width:220px">'+esc(t.name)+'</td>'+
        '<td>'+esc(t.cat || '-')+'</td>'+
        '<td><span class="cc-pill">'+esc(t.type || '-')+'</span></td>'+
        '<td><span class="cc-rankb '+rankClass(t.rank)+'">'+esc(t.rankDisplay)+'</span></td>'+
        '<td>'+esc(t.studio || '-')+'</td>'+
        '<td>'+esc(t.duration)+'d</td>'+
        '<td><span class="cc-stage-delta '+deltaCls+'">'+esc(deltaText)+'</span></td>'+
        '<td>'+esc(t.wishful || '-')+'</td>'+
      '</tr>';
    }).join('');
    const body = rows.length
      ? '<div class="cc-tbl-wrap"><table class="cc-table"><thead><tr><th>ID</th><th>Summary</th><th>Category</th><th>Type</th><th>Rank</th><th>Studio</th><th>Duration</th><th>vs avg</th><th>Wishful</th></tr></thead><tbody>'+tableRows+'</tbody></table></div>'
        + ((meta.count || 0) > rows.length ? '<p class="cc-muted" style="font-size:11.5px;margin-top:10px">Showing '+rows.length+' loaded ticket'+(rows.length===1?'':'s')+'; stage total is '+(meta.count || 0)+' in the full board.</p>' : '')
      : '<p class="cc-muted" style="font-size:13px">No tickets match the current filters for this stage'+((meta.count || 0) ? ' (stage total: '+(meta.count || 0)+').' : '.')+'</p>';
    openDrawer('Pipeline stage', meta.space + ' · ' + meta.title, rows.length + ' ticket' + (rows.length===1?'':'s') + ' in this stage', body);
    $('cc-dBody').querySelectorAll('tr[data-game-id]').forEach(el => el.addEventListener('click', () => openGameDrawer(el.dataset.gameId)));
  }
  function planItem(k,v){ return '<div class="cc-plan"><div class="t">'+esc(k)+'</div><div class="v">'+esc(v || '-')+'</div></div>'; }

  function renderAll(){
    const rows = filteredTickets();
    renderKPIs(rows);
    renderFlow(rows);
    renderTable(rows);
    renderCharts(rows);
  }
  function onShow(){
    requestAnimationFrame(() => {
      Object.values(charts).forEach(c => { if(c) c.resize(); });
      drawConnectors();
    });
  }

  $('cc-scrim').addEventListener('click', closeDrawer);
  $('cc-dClose').addEventListener('click', closeDrawer);
  document.addEventListener('keydown', e => { if(e.key === 'Escape') closeDrawer(); });
  window.closeDrawer = closeDrawer;
  window.openGameDrawer = openGameDrawer;
  window.openStageDrawer = openStageDrawer;
  window.ccOnShow = onShow;
  window.addEventListener('resize', () => requestAnimationFrame(drawConnectors));
  document.querySelectorAll('.vt-btn[data-view="flow"]').forEach(btn => btn.addEventListener('click', () => setTimeout(onShow, 40)));

  loadData();
  buildFilters();
  renderAll();
})();
"""
