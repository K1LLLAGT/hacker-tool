"""
report html v2 — single-pane LAN dashboard.
Combines arpwatch host table + sweep history + pipeline CVE/cred reports.
Usage:
    hackertool report html [--open]
    hackertool report html <report.json ...> [--open]
"""
from __future__ import annotations
import json, sys, datetime
from pathlib import Path

ROOT        = Path(__file__).parent.parent.parent
REPORTS_DIR = ROOT / "reports"
STATE_F     = REPORTS_DIR / "arpwatch_state.json"
OUT_FILE    = REPORTS_DIR / "dashboard.html"

# ── colour helpers ─────────────────────────────────────────────────────

def cvss_color(s: float) -> str:
    return "#c0392b" if s>=9 else "#e67e22" if s>=7 else "#f1c40f" if s>=4 else "#27ae60"

def cvss_badge(s: float) -> str:
    c = cvss_color(s)
    return (f'<span style="background:{c};color:#fff;padding:2px 8px;'
            f'border-radius:4px;font-size:.82em;font-weight:700">{s}</span>')

def badge(txt: str, color: str = "#2980b9") -> str:
    return (f'<span style="background:{color};color:#fff;padding:2px 9px;'
            f'border-radius:12px;font-size:.8em;font-weight:600;margin-left:5px">{txt}</span>')

# ── loaders ────────────────────────────────────────────────────────────

def load_arpwatch() -> tuple[dict, list]:
    """Returns (known_hosts_dict, history_list). Empty if no state file."""
    if not STATE_F.exists():
        return {}, []
    try:
        d = json.loads(STATE_F.read_text())
        return d.get("known", {}), d.get("history", [])
    except Exception:
        return {}, []

def load_reports(files: list[Path]) -> list[dict]:
    out = []
    for f in sorted(files, reverse=True):
        try:
            d = json.loads(f.read_text())
            d["_file"] = f.name
            out.append(d)
        except Exception:
            pass
    return out

# ── section renderers ──────────────────────────────────────────────────

def render_host_table(known: dict, pipeline_reports: list[dict]) -> str:
    if not known:
        return """
<section id="hosts">
  <h2 class="sec-title">🖥 LAN Hosts</h2>
  <div class="empty">No arpwatch data yet — run: <code>htctl arpwatch-scan</code></div>
</section>"""

    # Build map: ip → latest pipeline max_cvss
    ip_risk: dict[str, float] = {}
    for r in pipeline_reports:
        tgt = r.get("target","")
        for info in r.get("cve_hits",{}).values():
            if isinstance(info, dict):
                sc = info.get("max", info.get("max_cvss", 0))
                ip_risk[tgt] = max(ip_risk.get(tgt, 0), sc)

    rows = ""
    for ip, info in sorted(known.items(), key=lambda x: int(x[0].split(".")[-1])):
        mac    = info.get("mac","—")
        vendor = info.get("vendor","?")
        first  = info.get("first_seen","?")[:16]
        last   = info.get("last_seen","?")[:16]
        scans  = info.get("scan_count", 1)
        risk   = ip_risk.get(ip, 0)
        risk_cell = cvss_badge(risk) if risk else '<span style="color:#484f58">—</span>'
        dot_color = cvss_color(risk) if risk else "#27ae60"
        rows += f"""
      <tr>
        <td><span style="color:{dot_color};font-size:1.1em">●</span> <code>{ip}</code></td>
        <td><code style="font-size:.85em">{mac}</code></td>
        <td>{vendor}</td>
        <td>{risk_cell}</td>
        <td style="color:#8b949e;font-size:.85em">{first}</td>
        <td style="color:#8b949e;font-size:.85em">{last}</td>
        <td style="text-align:center">{scans}</td>
      </tr>"""

    return f"""
<section id="hosts">
  <h2 class="sec-title">🖥 LAN Hosts
    <span class="sec-count">{len(known)} known</span>
  </h2>
  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th>IP Address</th><th>MAC</th><th>Vendor (OUI)</th>
          <th>Max CVSS</th><th>First Seen</th><th>Last Seen</th><th>Sweeps</th>
        </tr>
      </thead>
      <tbody>{rows}</tbody>
    </table>
  </div>
</section>"""

def render_sweep_history(history: list) -> str:
    if not history:
        return ""
    recent = history[-20:][::-1]   # last 20, newest first
    rows = ""
    for h in recent:
        ts      = h.get("ts","?")
        live    = h.get("live", 0)
        new     = h.get("new", [])
        gone    = h.get("gone", [])
        my_ip   = h.get("my_ip","?")
        new_str = ", ".join(new) if new else "—"
        gone_str= ", ".join(gone) if gone else "—"
        new_cell= (f'<span style="color:#2ecc71">{new_str}</span>'
                   if new else '<span style="color:#484f58">—</span>')
        gone_cell=(f'<span style="color:#e74c3c">{gone_str}</span>'
                   if gone else '<span style="color:#484f58">—</span>')
        rows += f"""
      <tr>
        <td style="color:#8b949e;font-size:.85em">{ts}</td>
        <td style="text-align:center">{live}</td>
        <td><code style="font-size:.82em">{my_ip}</code></td>
        <td style="font-size:.85em">{new_cell}</td>
        <td style="font-size:.85em">{gone_cell}</td>
      </tr>"""

    return f"""
<section id="sweeps">
  <h2 class="sec-title">📡 Sweep History
    <span class="sec-count">last {len(recent)} of {len(history)}</span>
  </h2>
  <div class="table-wrap">
    <table>
      <thead>
        <tr><th>Timestamp</th><th>Live</th><th>Device IP</th><th>New</th><th>Gone</th></tr>
      </thead>
      <tbody>{rows}</tbody>
    </table>
  </div>
</section>"""

def render_pipeline_card(r: dict) -> str:
    target   = r.get("target","?")
    ts       = r.get("timestamp", r.get("ts","?"))
    ports    = r.get("open_ports",[])
    cv       = r.get("cve_hits",{})
    cr       = r.get("cred_hits",{})
    fname    = r.get("_file","")

    max_score = max(
        (i.get("max", i.get("max_cvss", 0))
         for i in cv.values() if isinstance(i, dict)),
        default=0
    )
    critical = [p for p,i in cv.items()
                if isinstance(i,dict) and i.get("max",i.get("max_cvss",0))>=9]
    border   = cvss_color(max_score) if cv else "#30363d"

    # CVE rows
    cve_rows = ""
    for p, info in sorted(cv.items(),
                          key=lambda x: -x[1].get("max",x[1].get("max_cvss",0))
                          if isinstance(x[1],dict) else 0):
        if not isinstance(info,dict): continue
        sc  = info.get("max", info.get("max_cvss",0))
        top = info.get("top", info.get("top_cve",{}))
        cid = top.get("id","?") if isinstance(top,dict) else "?"
        dsc = top.get("desc","?")[:88] if isinstance(top,dict) else "?"
        svc = info.get("service","?")
        rs  = "<br>".join(f"⚠ {x}" for x in info.get("risks",[])[:3])
        cve_rows += f"""
          <tr>
            <td><code>{p}</code></td>
            <td>{svc}</td>
            <td>{cvss_badge(sc)}</td>
            <td><strong style="font-size:.85em">{cid}</strong>
                <br><small style="color:#8b949e">{dsc}</small></td>
            <td><small style="color:#6e7681">{rs}</small></td>
          </tr>"""

    # Cred rows
    cred_rows = ""
    for p, info in cr.items():
        if not isinstance(info,dict): continue
        proto  = info.get("proto", info.get("protocol","?"))
        count  = info.get("count", info.get("default_cred_count",0))
        sample = info.get("sample",[])
        samp_h = " · ".join(
            f'<code>{d.get("vendor","?")}: '
            f'{d.get("username","") or "(blank)"}:'
            f'{d.get("password","") or "(blank)"}</code>'
            for d in sample[:3]
        )
        cred_rows += f"""
          <tr>
            <td><code>{p}</code></td>
            <td>{proto}</td>
            <td>{badge(f"{count} entries","#8e44ad")}</td>
            <td><small>{samp_h}</small></td>
          </tr>"""

    cve_sec = (f"""
        <div class="card-section">
          <h4 style="color:#e74c3c;margin-bottom:8px">CVE Exposure</h4>
          <div class="table-wrap">
            <table>
              <thead><tr><th>Port</th><th>Service</th><th>CVSS</th>
                         <th>Top CVE</th><th>Risks</th></tr></thead>
              <tbody>{cve_rows}</tbody>
            </table>
          </div>
        </div>""" if cve_rows else "")

    cred_sec = (f"""
        <div class="card-section">
          <h4 style="color:#8e44ad;margin-bottom:8px">Default Credential Risk</h4>
          <div class="table-wrap">
            <table>
              <thead><tr><th>Port</th><th>Proto</th><th>Entries</th>
                         <th>Sample credentials</th></tr></thead>
              <tbody>{cred_rows}</tbody>
            </table>
          </div>
        </div>""" if cred_rows else "")

    empty = ("""
        <div style="padding:10px;color:#27ae60;font-size:.9em">
          ✅ No CVE or default credential matches for open ports.
        </div>""" if not cve_rows and not cred_rows else "")

    return f"""
    <div class="card" style="border-left:4px solid {border}">
      <div class="card-header" style="background:{border}18">
        <div class="card-title-row">
          <span style="font-size:1.15em;font-weight:700">🎯 {target}</span>
          <span style="color:#8b949e;font-size:.85em;margin-left:12px">📅 {ts}</span>
          <div style="margin-left:auto">
            {badge(f"{len(ports)} ports")}
            {badge(f"{len(critical)} critical","#c0392b") if critical else ""}
            {badge(f"{len(cr)} cred risk","#8e44ad") if cr else ""}
          </div>
        </div>
        <div style="font-size:.72em;color:#484f58;margin-top:3px">{fname}</div>
      </div>
      {cve_sec}{cred_sec}{empty}
    </div>"""

def render_pipeline_section(reports: list[dict]) -> str:
    if not reports:
        return """
<section id="scans">
  <h2 class="sec-title">🔍 Pipeline Scan Reports</h2>
  <div class="empty">No scans yet — run: <code>hackertool net pipeline gateway --save</code></div>
</section>"""

    cards = "\n".join(render_pipeline_card(r) for r in reports)
    return f"""
<section id="scans">
  <h2 class="sec-title">🔍 Pipeline Scan Reports
    <span class="sec-count">{len(reports)} scan(s)</span>
  </h2>
  <div class="cards">{cards}</div>
</section>"""

# ── full page ──────────────────────────────────────────────────────────

def render_html(known: dict, history: list, reports: list[dict]) -> str:
    generated = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    targets   = len({r.get("target") for r in reports})
    total_crit= sum(
        1 for r in reports
        for i in r.get("cve_hits",{}).values()
        if isinstance(i,dict) and i.get("max",i.get("max_cvss",0))>=9
    )
    last_sweep  = history[-1]["ts"][:16] if history else "—"
    last_new    = history[-1].get("new",[]) if history else []
    live_count  = history[-1].get("live",0) if history else 0

    nav = """
    <nav>
      <a href="#hosts">Hosts</a>
      <a href="#sweeps">Sweeps</a>
      <a href="#scans">Scans</a>
    </nav>"""

    stats_html = f"""
<div class="stats">
  <div class="stat"><div class="num" style="color:#58a6ff">{len(known)}</div>
    <div class="lbl">Known Hosts</div></div>
  <div class="stat"><div class="num" style="color:#2ecc71">{live_count}</div>
    <div class="lbl">Live Now</div></div>
  <div class="stat"><div class="num" style="color:#2ecc71">{len(last_new)}</div>
    <div class="lbl">New (last sweep)</div></div>
  <div class="stat"><div class="num" style="color:#58a6ff">{len(reports)}</div>
    <div class="lbl">Scans</div></div>
  <div class="stat"><div class="num" style="color:#58a6ff">{targets}</div>
    <div class="lbl">Targets</div></div>
  <div class="stat"><div class="num" style="color:#c0392b">{total_crit}</div>
    <div class="lbl">Critical CVEs</div></div>
  <div class="stat"><div class="num" style="color:#e67e22">{sum(len(r.get("cve_hits",{})) for r in reports)}</div>
    <div class="lbl">CVE Matches</div></div>
  <div class="stat"><div class="num" style="color:#8e44ad">{sum(len(r.get("cred_hits",{})) for r in reports)}</div>
    <div class="lbl">Cred Risks</div></div>
</div>"""

    host_sec   = render_host_table(known, reports)
    sweep_sec  = render_sweep_history(history)
    pipe_sec   = render_pipeline_section(reports)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>hacker-tool · LAN Dashboard</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,monospace;
     background:#0d1117;color:#e6edf3;font-size:14px;line-height:1.55}}
header{{background:#161b22;border-bottom:1px solid #30363d;
        padding:14px 20px;position:sticky;top:0;z-index:20;
        display:flex;align-items:center;gap:16px;flex-wrap:wrap}}
header h1{{font-size:1.15em;color:#58a6ff;white-space:nowrap}}
header .meta{{color:#8b949e;font-size:.78em}}
nav{{margin-left:auto;display:flex;gap:4px}}
nav a{{color:#8b949e;text-decoration:none;padding:4px 10px;border-radius:6px;
       font-size:.82em;border:1px solid #30363d;transition:all .15s}}
nav a:hover{{background:#21262d;color:#e6edf3}}
.stats{{display:flex;flex-wrap:wrap;gap:10px;padding:14px 20px;
        background:#0d1117;border-bottom:1px solid #21262d}}
.stat{{background:#161b22;border:1px solid #30363d;border-radius:8px;
       padding:10px 16px;min-width:100px;text-align:center}}
.stat .num{{font-size:1.8em;font-weight:700}}
.stat .lbl{{color:#8b949e;font-size:.72em;text-transform:uppercase;margin-top:2px}}
main{{padding:20px;max-width:1140px;margin:0 auto}}
section{{margin-bottom:32px}}
.sec-title{{font-size:1.05em;font-weight:700;color:#e6edf3;
            padding-bottom:10px;border-bottom:1px solid #21262d;
            margin-bottom:14px;display:flex;align-items:center;gap:10px}}
.sec-count{{font-size:.75em;color:#8b949e;font-weight:400;
            background:#21262d;padding:2px 8px;border-radius:10px}}
.table-wrap{{overflow-x:auto}}
table{{width:100%;border-collapse:collapse;font-size:.88em}}
th{{background:#21262d;padding:7px 10px;text-align:left;color:#8b949e;
    font-weight:600;font-size:.75em;text-transform:uppercase;white-space:nowrap}}
td{{padding:7px 10px;border-top:1px solid #21262d;vertical-align:top}}
tr:hover td{{background:#1c2128}}
code{{background:#21262d;padding:1px 5px;border-radius:3px;font-size:.88em}}
.cards{{display:flex;flex-direction:column;gap:16px}}
.card{{background:#161b22;border:1px solid #30363d;border-radius:8px;overflow:hidden}}
.card-header{{padding:11px 16px}}
.card-title-row{{display:flex;align-items:center;flex-wrap:wrap;gap:6px}}
.card-section{{padding:10px 16px 14px}}
.empty{{background:#161b22;border:1px solid #30363d;border-radius:8px;
        padding:40px;text-align:center;color:#8b949e}}
footer{{text-align:center;color:#484f58;padding:28px;font-size:.78em}}
@media(max-width:600px){{
  .stat{{min-width:80px;padding:8px 10px}}
  .stat .num{{font-size:1.4em}}
  nav a{{padding:3px 7px}}
}}
</style>
</head>
<body>
<header>
  <h1>⚡ hacker-tool · LAN Dashboard</h1>
  <div class="meta">
    Generated {generated}
    &nbsp;·&nbsp; Last sweep {last_sweep}
    {f"&nbsp;·&nbsp; <span style='color:#2ecc71'>+{len(last_new)} new</span>" if last_new else ""}
  </div>
  {nav}
</header>

{stats_html}

<main>
  {host_sec}
  {sweep_sec if history else ""}
  {pipe_sec}
</main>

<footer>hacker-tool &nbsp;·&nbsp; generated {generated} &nbsp;·&nbsp; fully offline</footer>
</body>
</html>"""

# ── main ───────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    argv    = argv or sys.argv[1:]
    do_open = "--open" in argv
    files_a = [a for a in argv if not a.startswith("--")]

    REPORTS_DIR.mkdir(exist_ok=True)
    files   = ([Path(f) for f in files_a if Path(f).exists()]
               if files_a
               else sorted(REPORTS_DIR.glob("pipeline_*.json"), reverse=True))

    known, history = load_arpwatch()
    reports        = load_reports(files)
    html           = render_html(known, history, reports)

    OUT_FILE.write_text(html)

    total_crit = sum(
        1 for r in reports
        for i in r.get("cve_hits",{}).values()
        if isinstance(i,dict) and i.get("max",i.get("max_cvss",0))>=9
    )
    print(f"Dashboard v2 → {OUT_FILE}")
    print(f"  Hosts: {len(known)}  |  Sweeps: {len(history)}  |  "
          f"Scans: {len(reports)}  |  Critical CVEs: {total_crit}")

    if do_open:
        import subprocess
        try:
            subprocess.run(["termux-open", str(OUT_FILE)], timeout=5)
            print("  Opened in browser.")
        except Exception as e:
            print(f"  termux-open: {e}")
            print(f"  Manual: termux-open {OUT_FILE}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
