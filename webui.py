# MIT licensed
# Github: <https://github.com/Eve-PySpy/PySpy>**********************
''' The Material Design UI for PySpy, rendered inside a WebView2
browser control embedded in the wx frame (see gui.py). This module
holds the static HTML/CSS/JS page shell; gui.py pushes data into it
via render(payload) and receives user interactions (sorting is done
in-page; clicks, context menus and the menu button post messages back
to Python through window.pyspy.postMessage).
'''
# **********************************************************************

PAGE = r"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
/* Warm "Claude" palette: paper tones, terracotta accent. */
:root {
  --bg: #1f1e1d;
  --surface: #262624;
  --surface2: #302f2c;
  --on-bg: #f5f4ef;
  --on-muted: #a3a199;
  --divider: rgba(245,244,239,0.09);
  --hover: rgba(245,244,239,0.05);
  --primary: #d97757;
  --on-primary: #ffffff;
  --secondary: #83a9c4;
  --red: #e0685f;
  --pink: #c47ac0;
  --green: #86ac74;
  --shadow: 0 1px 2px rgba(0,0,0,.30), 0 4px 14px rgba(0,0,0,.22);
}
body.light {
  --bg: #eeece2;
  --surface: #faf9f5;
  --surface2: #f0eee6;
  --on-bg: #2b2a27;
  --on-muted: #77756c;
  --divider: rgba(60,55,45,0.13);
  --hover: rgba(60,55,45,0.045);
  --primary: #c15f3c;
  --on-primary: #ffffff;
  --secondary: #3a7ca5;
  --red: #b8433a;
  --pink: #a24a9e;
  --green: #4f7a43;
  --shadow: 0 1px 2px rgba(60,55,45,.10), 0 4px 14px rgba(60,55,45,.10);
}
* { box-sizing: border-box; margin: 0; padding: 0; }
html, body { height: 100%; overflow: hidden; }
body {
  background: var(--bg);
  color: var(--on-bg);
  font-family: Roboto, "Segoe UI Variable", "Segoe UI", system-ui, sans-serif;
  font-size: calc(13.5px * var(--scale, 1));
  user-select: none;
  cursor: default;
  display: flex;
  flex-direction: column;
}

/* ---------------- App bar ---------------- */
#appbar {
  flex: 0 0 auto;
  height: 52px;
  background: var(--bg);
  display: flex;
  align-items: center;
  padding: 0 12px 0 6px;
  gap: 10px;
  z-index: 30;
}
#menubtn {
  width: 40px; height: 40px;
  border: none; border-radius: 50%;
  background: transparent;
  color: var(--on-bg);
  font-size: 20px;
  display: flex; align-items: center; justify-content: center;
  cursor: pointer;
}
#menubtn:hover { background: var(--hover); }
#apptitle { font-size: 16px; font-weight: 500; letter-spacing: .3px; }
#apptitle span { color: var(--on-muted); font-weight: 400; }
#location {
  display: none;
  align-items: center;
  gap: 6px;
  background: color-mix(in srgb, var(--primary) 16%, transparent);
  color: var(--primary);
  border-radius: 16px;
  padding: 5px 14px 5px 10px;
  font-size: 13px;
  font-weight: 500;
}
#location .dot { font-size: 14px; }
#pilotcount { margin-left: auto; color: var(--on-muted); font-size: 12.5px; }

/* ---------------- Summary chips ---------------- */
#summary {
  flex: 0 0 auto;
  display: none;
  flex-wrap: wrap;
  gap: 8px;
  padding: 10px 14px 4px 14px;
}
.chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: var(--surface2);
  color: var(--on-bg);
  border-radius: 8px;
  padding: 5px 12px;
  font-size: 12.5px;
  font-weight: 500;
  border: 1px solid var(--divider);
}
.chip .n { color: var(--primary); font-weight: 700; }
.chip.warn { color: var(--red); border-color: color-mix(in srgb, var(--red) 40%, transparent); }
.chip.cyno { color: var(--secondary); border-color: color-mix(in srgb, var(--secondary) 40%, transparent); }

/* ---------------- Table card ---------------- */
#card {
  flex: 1 1 auto;
  margin: 10px 14px;
  background: var(--surface);
  border-radius: 12px;
  box-shadow: var(--shadow);
  overflow: auto;
  position: relative;
}
#card::-webkit-scrollbar { width: 10px; height: 10px; }
#card::-webkit-scrollbar-thumb { background: var(--surface2); border-radius: 5px; }
#card::-webkit-scrollbar-corner { background: transparent; }
table { border-collapse: collapse; width: 100%; white-space: nowrap; }
thead th {
  position: sticky; top: 0;
  background: var(--surface);
  color: var(--on-muted);
  font-size: 12.5px;
  font-weight: 500;
  letter-spacing: 0;
  text-align: left;
  padding: 13px 14px;
  border-bottom: 1px solid var(--divider);
  cursor: pointer;
  z-index: 10;
}
thead th:hover { color: var(--on-bg); }
thead th.num { text-align: right; }
thead th .arrow { color: var(--primary); margin-left: 3px; }
tbody td {
  padding: 7px 14px;
  border-bottom: 1px solid var(--divider);
  font-size: inherit;
}
tbody td.num { text-align: right; font-variant-numeric: tabular-nums; }
tbody tr:hover { background: var(--hover); }
tbody tr { cursor: pointer; }
td.muted, span.muted { color: var(--on-muted); }

/* Character cell */
.charcell { display: flex; align-items: center; gap: 10px; }
.avatar {
  width: 30px; height: 30px;
  border-radius: 50%;
  background: var(--surface2);
  flex: 0 0 auto;
}
.charname { font-weight: 500; }

/* Row accent classes */
tr.hl1 td, td .hl1 { color: var(--red); }
tr.hl2 td { color: var(--secondary); }
tr.hl3 td { color: var(--pink); }

/* Warning chips */
.wchip {
  display: inline-block;
  border-radius: 10px;
  font-size: 10.5px;
  font-weight: 700;
  letter-spacing: .5px;
  padding: 2px 9px;
  margin-right: 4px;
  color: #10131a;
}
.wchip.red { background: var(--red); }
.wchip.blue { background: var(--secondary); }

/* Danger meter */
.danger { display: inline-flex; align-items: center; gap: 8px; justify-content: flex-end; }
.dbar { width: 44px; height: 4px; border-radius: 2px; background: var(--surface2); overflow: hidden; }
.dbar i { display: block; height: 100%; border-radius: 2px; }

/* Empty state */
#empty {
  position: absolute; inset: 0;
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  gap: 10px; color: var(--on-muted);
}
#empty .big { font-size: 17px; font-weight: 500; color: var(--on-bg); }

/* ---------------- Bottom bar ---------------- */
#bottombar {
  flex: 0 0 auto;
  height: 40px;
  background: var(--bg);
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 0 14px;
  z-index: 30;
}
#status {
  flex: 1 1 auto;
  color: var(--on-muted);
  font-size: 12.5px;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
#alpha { width: 110px; accent-color: var(--primary); }

/* ---------------- Snackbar ---------------- */
#snackbar {
  position: fixed;
  left: 50%; bottom: 54px;
  transform: translateX(-50%) translateY(20px);
  background: var(--surface2);
  color: var(--on-bg);
  border-left: 3px solid var(--red);
  border-radius: 6px;
  box-shadow: var(--shadow);
  padding: 12px 18px;
  font-size: 13px;
  max-width: 80%;
  opacity: 0;
  transition: all .25s ease;
  pointer-events: none;
  z-index: 50;
}
#snackbar.show { opacity: 1; transform: translateX(-50%) translateY(0); }
</style>
</head>
<body>
<div id="appbar">
  <button id="menubtn" title="Menu">&#9776;</button>
  <div id="apptitle">PySpy <span>[Reworked]</span></div>
  <div id="location"><span class="dot">&#10148;</span><span id="locname"></span></div>
  <div id="pilotcount"></div>
</div>
<div id="summary"></div>
<div id="card">
  <div id="empty">
    <div class="big">Awaiting targets</div>
    <div>Copy character names from local chat (CTRL+A, CTRL+C in the member list)<br>
    or let chat log intel and local-speaker detection feed the list automatically.</div>
  </div>
  <table id="tbl" style="display:none">
    <thead><tr id="headrow"></tr></thead>
    <tbody id="tbody"></tbody>
  </table>
</div>
<div id="bottombar">
  <div id="status">Please copy some EVE character names to clipboard...</div>
  <input id="alpha" type="range" min="50" max="255" value="250" title="Window transparency">
</div>
<div id="snackbar"></div>

<script>
var state = { payload: null, sortKey: "name", sortDesc: false };

function post(obj) {
  try { window.pyspy.postMessage(JSON.stringify(obj)); } catch (e) {}
}

function esc(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;")
                  .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function setTheme(name) {
  document.body.className = (name === "light") ? "light" : "";
}
function setScale(x) {
  document.body.style.setProperty("--scale", x);
}
function setStatus(msg) {
  document.getElementById("status").textContent = msg;
}
function setLocation(sys) {
  var loc = document.getElementById("location");
  document.getElementById("locname").textContent = sys;
  loc.style.display = sys ? "inline-flex" : "none";
}
var snackTimer = null;
function snackbar(msg) {
  var el = document.getElementById("snackbar");
  el.textContent = msg;
  el.classList.add("show");
  clearTimeout(snackTimer);
  snackTimer = setTimeout(function () { el.classList.remove("show"); }, 6000);
}

function dangerCell(v) {
  if (v === null || v === undefined) return '<span class="muted">n.a.</span>';
  var col = v >= 70 ? "var(--red)" : (v >= 40 ? "var(--primary)" : "var(--green)");
  return '<span class="danger"><span class="dbar"><i style="width:' + v +
         '%;background:' + col + '"></i></span>' + v + "%</span>";
}

function warningsCell(w) {
  if (!w || !w.length) return '<span class="muted">-</span>';
  return w.map(function (t) {
    var cls = (t === "CYNO") ? "blue" : "red";
    return '<span class="wchip ' + cls + '">' + esc(t) + "</span>";
  }).join("");
}

function cellHtml(col, row) {
  var v = row.d[col.key];
  if (col.key === "warning") return warningsCell(row.warnings);
  if (col.key === "danger") return dangerCell(row.dangerVal);
  if (col.key === "name") {
    return '<span class="charcell"><img class="avatar" loading="lazy" src="' +
           "https://images.evetech.net/characters/" + row.charId +
           '/portrait?size=64" onerror="this.style.visibility=\'hidden\'">' +
           '<span class="charname">' + esc(v) + "</span></span>";
  }
  if (v === "-" || v === "n.a." || v === "" || v === null || v === undefined) {
    return '<span class="muted">' + esc(v === "" || v == null ? "-" : v) + "</span>";
  }
  return esc(v);
}

function render(payload) {
  if (payload) state.payload = payload;
  var p = state.payload;
  var tbl = document.getElementById("tbl");
  var empty = document.getElementById("empty");
  var summary = document.getElementById("summary");
  var count = document.getElementById("pilotcount");
  if (!p || !p.rows || !p.rows.length) {
    tbl.style.display = "none";
    empty.style.display = "flex";
    summary.style.display = "none";
    count.textContent = "";
    return;
  }
  empty.style.display = "none";
  tbl.style.display = "table";

  // Summary chips
  var s = p.summary || {};
  var chips = [];
  chips.push('<span class="chip"><span class="n">' + s.pilots + "</span> pilot" +
             (s.pilots !== 1 ? "s" : "") + "</span>");
  (s.affils || []).forEach(function (a) {
    chips.push('<span class="chip">' + esc(a[0]) +
               ' <span class="n">' + a[1] + "</span></span>");
  });
  if (s.more > 0) chips.push('<span class="chip">+' + s.more + " more</span>");
  if (s.cyno > 0) chips.push('<span class="chip cyno">Cyno risk <span class="n">' + s.cyno + "</span></span>");
  if (s.blops > 0) chips.push('<span class="chip warn">BLOPS-active <span class="n">' + s.blops + "</span></span>");
  summary.innerHTML = chips.join("");
  summary.style.display = "flex";
  count.textContent = s.pilots + " pilot" + (s.pilots !== 1 ? "s" : "") +
                      (s.ignored ? " (" + s.ignored + " ignored)" : "");

  // Header
  var cols = p.columns.filter(function (c) { return c.visible; });
  var head = cols.map(function (c) {
    var arrow = "";
    if (c.key === state.sortKey) arrow = '<span class="arrow">' + (state.sortDesc ? "&#9660;" : "&#9650;") + "</span>";
    return '<th class="' + (c.num ? "num" : "") + '" data-key="' + c.key + '">' +
           esc(c.label) + arrow + "</th>";
  }).join("");
  document.getElementById("headrow").innerHTML = head;

  // Rows (sorted client-side)
  var rows = p.rows.filter(function (r) { return !r.hidden; }).slice();
  var key = state.sortKey, desc = state.sortDesc;
  rows.sort(function (a, b) {
    var x = a.s[key], y = b.s[key];
    if (x === null || x === undefined) x = -Infinity;
    if (y === null || y === undefined) y = -Infinity;
    if (typeof x === "string" || typeof y === "string") {
      x = String(x).toLowerCase(); y = String(y).toLowerCase();
    }
    var cmp = x < y ? -1 : (x > y ? 1 : 0);
    if (cmp === 0) {
      var nx = String(a.s.name).toLowerCase(), ny = String(b.s.name).toLowerCase();
      cmp = nx < ny ? -1 : (nx > ny ? 1 : 0);
    }
    return desc ? -cmp : cmp;
  });

  var html = rows.map(function (r, i) {
    var tds = cols.map(function (c) {
      return '<td class="' + (c.num ? "num" : "") + '">' + cellHtml(c, r) + "</td>";
    }).join("");
    return '<tr class="' + r.cls + '" data-idx="' + r.idx + '">' + tds + "</tr>";
  }).join("");
  document.getElementById("tbody").innerHTML = html;
}

/* ------------- interactions ------------- */
document.getElementById("menubtn").addEventListener("click", function () {
  post({ action: "menu" });
});
document.getElementById("headrow").addEventListener("click", function (e) {
  var th = e.target.closest("th");
  if (!th) return;
  var key = th.getAttribute("data-key");
  if (state.sortKey === key) state.sortDesc = !state.sortDesc;
  else { state.sortKey = key; state.sortDesc = true; }
  render(null);
});
document.getElementById("tbody").addEventListener("dblclick", function (e) {
  var tr = e.target.closest("tr");
  if (!tr) return;
  var td = e.target.closest("td");
  var colKey = "";
  if (td) {
    var cols = state.payload.columns.filter(function (c) { return c.visible; });
    colKey = (cols[td.cellIndex] || {}).key || "";
  }
  post({ action: "zkill", idx: parseInt(tr.getAttribute("data-idx"), 10), col: colKey });
});
document.getElementById("tbody").addEventListener("contextmenu", function (e) {
  e.preventDefault();
  var tr = e.target.closest("tr");
  if (!tr) return;
  post({ action: "context", idx: parseInt(tr.getAttribute("data-idx"), 10) });
});
document.addEventListener("contextmenu", function (e) { e.preventDefault(); });
document.getElementById("alpha").addEventListener("input", function (e) {
  post({ action: "alpha", value: parseInt(e.target.value, 10) });
});
document.addEventListener("dblclick", function (e) { e.preventDefault(); });
</script>
</body>
</html>
"""
