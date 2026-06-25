"""
"Glossary" view for the Game Status dashboard.

Exports GLOSSARY_HTML — injected into the page by generate_game_status_html.py
via {{GLOSSARY_HTML}}. Renders the standalone production-workflow glossary page
(scratch/glossary_source.html) inside a sandboxed iframe, so its own CSS/JS
(generic class names like .role, .tag, .section) can never collide with the
dashboard's styles.

To update the glossary content, edit scratch/glossary_source.html directly and
regenerate — it's a normal self-contained HTML file, not a template.
"""

import base64
from pathlib import Path

_SOURCE = Path(__file__).resolve().parent / "glossary_source.html"
_GLOSSARY_B64 = base64.b64encode(_SOURCE.read_bytes()).decode("ascii")

GLOSSARY_HTML = f"""\
<div id="view-glossary" style="display:none">
  <iframe id="glossary-frame" title="Glossary"
          style="width:100%;height:calc(100vh - 53px);border:none;display:block;background:#fff"></iframe>
</div>
<script>
  (function(){{
    var b64 = "{_GLOSSARY_B64}";
    var bytes = Uint8Array.from(atob(b64), function(c){{ return c.charCodeAt(0); }});
    var html = new TextDecoder('utf-8').decode(bytes);
    document.getElementById('glossary-frame').srcdoc = html;
  }})();
</script>
"""
