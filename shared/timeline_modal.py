"""
Reusable game-ticket *timeline* modal (dark theme).

Exports TIMELINE_CSS / TIMELINE_HTML / TIMELINE_JS and a `render_into(page_html)`
helper. Any board's HTML generator embeds the three brace-free sentinels

    /*__TIMELINE_CSS__*/      <!--__TIMELINE_HTML__-->      /*__TIMELINE_JS__*/

then calls `render_into(final_html)` **last** — after its own templating (Game
Status uses str.replace, Board Priority Queue uses str.format, so the sentinels
must contain no braces). The page then exposes a single public function:

    openTimelineModal(key, { summary, studio, market, batch, category,
                             wishful, status, created })

which fetches GET /api/ticket/<key>/timeline (served by game-status-analysis/server.py,
mounted at root in the shared Flask process) and renders the per-stage Gantt.
On a non-GAME key or any fetch error it falls back to a planned-duration
estimate so the modal never breaks.

Bar model (per row): a blue *Actual duration* bar, extended by a green *Time
saved* segment when a stage finished before its ETA (Jira due date), or an orange
*Overrun past ETA* segment when it finished after. Future stages show a dashed
*Not started* track. Development's sub-stages (BE/BO/Platform/FE/Math) render
indented inside a highlighted group panel.
"""

CSS_SENTINEL = "/*__TIMELINE_CSS__*/"
HTML_SENTINEL = "<!--__TIMELINE_HTML__-->"
JS_SENTINEL = "/*__TIMELINE_JS__*/"

TIMELINE_CSS = """\
  /* ── Timeline Modal (shared) ──────────────────────────────────────────────── */
  #tl-modal-bg {
    display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.62);
    align-items: center; justify-content: center; z-index: 1000; padding: 24px;
    font-family: 'Outfit', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  }
  #tl-modal-bg.open { display: flex; }
  #tl-modal {
    background: #1c1d22; border-radius: 16px; border: 1px solid #2c2e36;
    width: 100%; max-width: 760px; max-height: 90vh; overflow-y: auto;
    padding: 26px 30px 28px; color: #d7dae1; box-shadow: 0 24px 60px rgba(0,0,0,0.5);
  }
  .tl-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; }
  .tl-title { font-size: 17px; font-weight: 600; color: #f2f4f8; line-height: 1.3; }
  .tl-sub   { font-size: 12.5px; color: #8a8f9c; margin-top: 5px; }
  .tl-close { background: #24262e; border: 1px solid #33353f; cursor: pointer; font-size: 15px;
              color: #9aa0ac; line-height: 1; padding: 6px 10px; border-radius: 8px; }
  .tl-close:hover { color: #f2f4f8; border-color: #4a4d59; }

  .tl-info { display: grid; grid-template-columns: 1fr 1fr; gap: 9px 28px;
             margin: 20px 0 4px; padding-bottom: 20px; border-bottom: 1px solid #2a2c34; }
  .tl-info-row   { display: flex; gap: 10px; font-size: 13px; }
  .tl-info-label { color: #7d8290; min-width: 104px; }
  .tl-info-val   { color: #eceef3; font-weight: 500; }

  .tl-section { font-size: 11px; font-weight: 600; color: #6f7484; text-transform: uppercase;
                letter-spacing: .08em; margin: 22px 0 12px; }

  .tl-axis { display: grid; grid-template-columns: 150px 1fr 52px; gap: 12px; margin-bottom: 10px; }
  .tl-axis-labels { display: flex; justify-content: space-between; font-size: 10.5px; color: #6f7484; }
  .tl-wrap { display: flex; flex-direction: column; }

  .tl-row { display: grid; grid-template-columns: 150px 1fr 52px; gap: 12px; align-items: center;
            padding: 7px 0; }
  .tl-name { font-size: 12.5px; color: #c2c6d0; text-align: right; padding-right: 2px;
             white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .tl-row.parent .tl-name { font-weight: 600; color: #e7e9ef; }
  .tl-bararea { position: relative; height: 22px; }
  .tl-seg { position: absolute; height: 18px; top: 2px; border-radius: 4px; box-sizing: border-box; }
  .tl-seg.actual   { background: #4d8bf0; }
  .tl-seg.saved    { background: #8ec45a; }
  .tl-seg.overrun  { background: #e8993c; }
  .tl-seg.progress { background: #4d8bf0; }
  .tl-seg.future   { background: transparent; border: 1px dashed #3f4350; height: 20px; top: 1px; }
  .tl-delta { font-size: 11.5px; text-align: right; color: #6f7484; }
  .tl-delta.saved   { color: #8ec45a; font-weight: 600; }
  .tl-delta.overrun { color: #e8736e; font-weight: 600; }
  .tl-delta.zero    { color: #8ec45a; font-weight: 600; }
  .tl-delta.progress{ color: #6f7484; }

  /* Highlighted sub-stage group (Development children) */
  .tl-group { background: #15161a; border-radius: 10px; padding: 4px 12px 4px 0; margin: 2px 0; }
  .tl-group .tl-name { color: #aab0bc; }

  .tl-legend { display: flex; flex-wrap: wrap; gap: 18px; margin-top: 22px; padding-top: 16px;
               border-top: 1px solid #2a2c34; font-size: 11.5px; color: #8a8f9c; }
  .tl-leg { display: flex; align-items: center; gap: 7px; }
  .tl-leg-box { width: 20px; height: 10px; border-radius: 3px; }

  .tl-loading { padding: 40px 24px; display: flex; flex-direction: column; align-items: center;
                gap: 12px; color: #7d8290; font-size: 12.5px; }
  .tl-spinner { width: 26px; height: 26px; border: 2.5px solid #2c2e36; border-top-color: #4d8bf0;
                border-radius: 50%; animation: tl-spin 0.7s linear infinite; }
  @keyframes tl-spin { to { transform: rotate(360deg); } }
"""

TIMELINE_HTML = """\
<!-- Timeline Modal (shared) -->
<div id="tl-modal-bg">
  <div id="tl-modal">
    <div class="tl-head">
      <div>
        <div class="tl-title" id="tl-title">&#x2014;</div>
        <div class="tl-sub"   id="tl-sub">&#x2014;</div>
      </div>
      <button class="tl-close" onclick="closeTimelineModal()">&#x2715;</button>
    </div>
    <div class="tl-info" id="tl-info"></div>
    <div class="tl-section" id="tl-section">Stage timeline</div>
    <div class="tl-axis">
      <div></div>
      <div class="tl-axis-labels" id="tl-axis"></div>
      <div></div>
    </div>
    <div class="tl-wrap" id="tl-rows"></div>
    <div class="tl-legend">
      <div class="tl-leg"><span class="tl-leg-box" style="background:#4d8bf0"></span>Actual duration</div>
      <div class="tl-leg"><span class="tl-leg-box" style="background:#8ec45a"></span>Time saved</div>
      <div class="tl-leg"><span class="tl-leg-box" style="background:#e8993c"></span>Overrun past ETA</div>
      <div class="tl-leg"><span class="tl-leg-box" style="border:1px dashed #3f4350"></span>Not started</div>
    </div>
  </div>
</div>
"""

TIMELINE_JS = r"""
  // ── Timeline Modal (shared) ─────────────────────────────────────────────────

  // Planned working duration per top-level GAME stage (estimate fallback only).
  // Keep in sync with scratch/overview_logic.py STAGE_DURATIONS.
  const TL_STAGES = ['Planned', 'Math', 'Contract Alignment', 'Development',
                     'Integration QC', 'Optimization', 'Packaging', 'Done'];
  const TL_DURATIONS = { 'Planned': 4, 'Math': 5, 'Contract Alignment': 3, 'Development': 20,
                         'Integration QC': 10, 'Optimization': 5, 'Packaging': 4, 'Done': 1 };

  function tlEsc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }
  function tlDate(s) { return s ? new Date(String(s).substring(0, 10)) : null; }
  function tlDiff(a, b) { return Math.round((b - a) / 86400000); }
  function tlFmt(d) { return d ? d.toISOString().substring(5, 10) : ''; }

  // Build an estimated stage list from the created date (no real changelog).
  function tlEstimateStages(created) {
    let cur = tlDate(created) || new Date();
    cur = new Date(cur);
    return TL_STAGES.map(name => {
      const dur = TL_DURATIONS[name] || 5;
      const start = new Date(cur);
      const end = new Date(cur); end.setDate(end.getDate() + dur - 1);
      cur = new Date(end); cur.setDate(cur.getDate() + 1);
      // estimate: leave actuals null so every row renders as "not started"
      return { name, level: 0, actual_start: null, actual_end: null, eta: end.toISOString() };
    });
  }

  function tlRenderRows(stages) {
    const today = new Date();
    const dates = [today];
    stages.forEach(s => {
      [s.actual_start, s.actual_end, s.eta].forEach(v => { const d = tlDate(v); if (d) dates.push(d); });
    });
    const minD = new Date(Math.min(...dates.map(d => d.getTime())));
    const maxD = new Date(Math.max(...dates.map(d => d.getTime())));
    const span = tlDiff(minD, maxD) || 1;
    const pct = d => (tlDiff(minD, d) / span * 100);

    const mid = new Date((minD.getTime() + maxD.getTime()) / 2);
    document.getElementById('tl-axis').innerHTML =
      '<span>' + tlFmt(minD) + '</span><span>' + tlFmt(mid) + '</span><span>' + tlFmt(maxD) + '</span>';

    const wrap = document.getElementById('tl-rows');
    wrap.innerHTML = '';
    let group = null;  // open .tl-group container while consuming level-1 rows

    stages.forEach(s => {
      const level = s.level || 0;
      const as_ = tlDate(s.actual_start), ae = tlDate(s.actual_end), eta = tlDate(s.eta);

      let segs = '', delta = '—', deltaCls = 'progress';

      if (as_ && ae) {
        // Completed — blue actual, plus saved (green) or overrun (orange) vs ETA.
        const barEnd = (eta && eta < ae) ? eta : ae;
        segs += '<div class="tl-seg actual" style="left:' + pct(as_).toFixed(1) + '%;width:' +
                Math.max(pct(barEnd) - pct(as_), 0.6).toFixed(1) + '%"></div>';
        if (eta) {
          const d = tlDiff(eta, ae);  // >0 overrun, <0 saved
          if (d < 0) {
            segs += '<div class="tl-seg saved" style="left:' + pct(ae).toFixed(1) + '%;width:' +
                    Math.max(pct(eta) - pct(ae), 0.6).toFixed(1) + '%"></div>';
            delta = d + 'd'; deltaCls = 'saved';
          } else if (d > 0) {
            segs += '<div class="tl-seg overrun" style="left:' + pct(eta).toFixed(1) + '%;width:' +
                    Math.max(pct(ae) - pct(eta), 0.6).toFixed(1) + '%"></div>';
            delta = '+' + d + 'd'; deltaCls = 'overrun';
          } else { delta = '±0d'; deltaCls = 'zero'; }
        } else { delta = '±0d'; deltaCls = 'zero'; }
      } else if (as_ && !ae) {
        // In progress — blue from start to today.
        segs += '<div class="tl-seg progress" style="left:' + pct(as_).toFixed(1) + '%;width:' +
                Math.max(pct(today) - pct(as_), 0.6).toFixed(1) + '%"></div>';
        delta = 'in progress'; deltaCls = 'progress';
      } else {
        // Not started — dashed full-width track.
        segs += '<div class="tl-seg future" style="left:0;width:100%"></div>';
        delta = '—'; deltaCls = 'progress';
      }

      const row =
        '<div class="tl-row ' + (level === 0 ? 'parent' : 'child') + '">' +
          '<div class="tl-name">' + tlEsc(s.name) + '</div>' +
          '<div class="tl-bararea">' + segs + '</div>' +
          '<div class="tl-delta ' + deltaCls + '">' + delta + '</div>' +
        '</div>';

      if (level === 1) {
        if (!group) { group = document.createElement('div'); group.className = 'tl-group'; wrap.appendChild(group); }
        group.insertAdjacentHTML('beforeend', row);
      } else {
        group = null;
        wrap.insertAdjacentHTML('beforeend', row);
      }
    });
  }

  async function openTimelineModal(key, opts) {
    opts = opts || {};
    document.getElementById('tl-title').textContent = key + ' — ' + (opts.summary || '');
    document.getElementById('tl-sub').textContent =
      'Studio: ' + (opts.studio || '—') + ' · Market: ' + (opts.market || '—') +
      ' · Batch: ' + (opts.batch || '—');

    const created = opts.created || '';
    const durDays = created ? Math.floor((Date.now() - new Date(String(created).substring(0, 10))) / 86400000) : null;
    document.getElementById('tl-info').innerHTML =
      '<div class="tl-info-row"><span class="tl-info-label">Current status</span><span class="tl-info-val">' + tlEsc(opts.status || '—') + '</span></div>' +
      '<div class="tl-info-row"><span class="tl-info-label">Duration</span><span class="tl-info-val">' + (durDays != null ? (durDays < 1 ? '<1d' : durDays + 'd') : '—') + '</span></div>' +
      '<div class="tl-info-row"><span class="tl-info-label">Wishful date</span><span class="tl-info-val">' + tlEsc(opts.wishful || '—') + '</span></div>' +
      '<div class="tl-info-row"><span class="tl-info-label">Game category</span><span class="tl-info-val">' + tlEsc(opts.category || '—') + '</span></div>';

    document.getElementById('tl-section').textContent = 'Stage timeline';
    document.getElementById('tl-axis').innerHTML = '';
    document.getElementById('tl-rows').innerHTML =
      '<div class="tl-loading"><div class="tl-spinner"></div><span>Loading timeline…</span></div>';
    document.getElementById('tl-modal-bg').classList.add('open');

    const estimate = () => {
      document.getElementById('tl-section').textContent = 'Stage timeline (estimated)';
      tlRenderRows(tlEstimateStages(created));
    };

    if (!String(key).startsWith('GAME-')) { estimate(); return; }

    // The timeline endpoint lives on the game-status blueprint, mounted at root
    // both standalone and inside the Flask shell.
    const path = '/api/ticket/' + encodeURIComponent(key) + '/timeline';
    try {
      const resp = await fetch(path);
      if (resp.ok) {
        const data = await resp.json();
        const stages = data.stages || [];
        if (stages.length && !data.estimated) { tlRenderRows(stages); return; }
      }
    } catch (err) { /* fall through to estimate */ }
    estimate();
  }

  function closeTimelineModal() {
    document.getElementById('tl-modal-bg').classList.remove('open');
  }

  document.getElementById('tl-modal-bg').addEventListener('click', function (e) {
    if (e.target === document.getElementById('tl-modal-bg')) closeTimelineModal();
  });

  window.openTimelineModal = openTimelineModal;
  window.closeTimelineModal = closeTimelineModal;
"""


def render_into(page_html: str) -> str:
    """Replace the three brace-free sentinels with the modal CSS/HTML/JS.

    Call this LAST, after the host generator finishes its own templating, so the
    injected braces never collide with str.format() / str.replace() placeholders.
    """
    return (
        page_html
        .replace(CSS_SENTINEL, TIMELINE_CSS)
        .replace(HTML_SENTINEL, TIMELINE_HTML)
        .replace(JS_SENTINEL, TIMELINE_JS)
    )
