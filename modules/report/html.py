"""
report html — render all pipeline JSON reports into a single HTML dashboard.
Usage:
    hackertool report html [--open]
    hackertool report html <report.json> [--open]
"""
from __future__ import annotations
import json, sys, datetime
from pathlib import Path

ROOT        = Path(__file__).parent.parent.parent
REPORTS_DIR = ROOT / "reports"
OUT_FILE    = REPORTS_DIR / "dashboard.html"

def cvss_color(score: float) -> str:
    if score >= 9.0: return "#c0392b"   # red
    if score >= 7.0: return "#e67e22"   # orange
    if score >= 4.0: return "#f1c40f"   # yellow
    return "#27ae60"                     # green

def cvss_badge(score: float) -> str:
    color = cvss_color(score)
    return f'<span style="background:{color};color:#fff;padding:2px 7px;border-radius:4px;font-size:0.85em;font-weight:bold">{score}</span>'

def severity_label(score: float) -> str:
    if score >= 9.0: return "CRITICAL"
    if score >= 7.0: return "HIGH"
    if score >= 4.0: return "MEDIUM"
    return "LOW"

def load_reports(files: list[Path]) -> list[dict]:
    reports = []
    for f in sorted(files, reverse=True):
        try:
            data = json.loads(f.read_text())
            data["_file"] = f.name
            reports.append(data)
        except Exception:
            pass
    return reports

def render_scan_card(r: dict) -> str:
    target    = r.get("target", "?")
    ts        = r.get("timestamp", r.get("ts", "?"))
    ports     = r.get("open_ports", [])
    cve_hits  = r.get("cve_hits", {})
    cred_hits = r.get("cred_hits", {})
    fname     = r.get("_file", "")

    critical = [p for p, i in cve_hits.items()
                if isinstance(i, dict) and i.get("max", i.get("max_cvss", 0)) >= 9.0]
    max_score = max((i.get("max", i.get("max_cvss", 0))
                     for i in cve_hits.values() if isinstance(i, dict)), default=0)

    header_color = cvss_color(max_score) if cve_hits else "#2c3e50"

    # CVE rows
    cve_rows = ""
    for port, info in sorted(cve_hits.items(),
                              key=lambda x: -x[1].get("max", x[1].get("max_cvss", 0))
                              if isinstance(x[1], dict) else 0):
        if not isinstance(info, dict): continue
        svc   = info.get("service", "?")
        score = info.get("max", info.get("max_cvss", 0))
        top   = info.get("top", info.get("top_cve", {}))
        desc  = top.get("desc", "?")[:90] if isinstance(top, dict) else "?"
        cid   = top.get("id", "?") if isinstance(top, dict) else "?"
        risks = "<br>".join(f"⚠ {r}" for r in info.get("risks", [])[:3])
        cve_rows += f"""
        <tr>
          <td><code>{port}</code></td>
          <td>{svc}</td>
          <td>{cvss_badge(score)}</td>
          <td><strong>{cid}</strong><br><small>{desc}</small></td>
          <td><small style="color:#888">{risks}</small></td>
        </tr>"""

    # Cred rows
    cred_rows = ""
    for port, info in cred_hits.items():
        if not isinstance(info, dict): continue
        proto   = info.get("proto", info.get("protocol", "?"))
        count   = info.get("count", info.get("default_cred_count", 0))
        samples = info.get("sample", [])
        sample_html = " &nbsp;·&nbsp; ".join(
            f"<code>{d.get('vendor','?')}: {d.get('username','') or '(blank)'}:{d.get('password','') or '(blank)'}</code>"
            for d in samples[:3]
        )
        cred_rows += f"""
        <tr>
          <td><code>{port}</code></td>
          <td>{proto}</td>
          <td><span style="background:#8e44ad;color:#fff;padding:2px 7px;border-radius:4px">{count} entries</span></td>
          <td><small>{sample_html}</small></td>
        </tr>"""

    return f"""
<div class="card" style="border-left:5px solid {header_color};margin-bottom:28px">
  <div class="card-header" style="background:{header_color}22;padding:12px 16px;border-radius:6px 6px 0 0">
    <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px">
      <div>
        <span style="font-size:1.3em;font-weight:bold">🎯 {target}</span>
        <span style="margin-left:12px;color:#666;font-size:0.9em">📅 {ts}</span>
      </div>
      <div>
        <span class="badge" style="background:#2980b9">{len(ports)} ports</span>
        <span class="badge" style="background:{header_color}">{len(critical)} critical CVE</span>
        <span class="badge" style="background:#8e44ad">{len(cred_hits)} cred risk</span>
      </div>
    </div>
    <div style="font-size:0.75em;color:#999;margin-top:4px">{fname}</div>
  </div>

  {"" if not cve_rows else f'''
  <div style="padding:12px 16px">
    <h4 style="margin:0 0 8px;color:#c0392b">CVE Exposure</h4>
    <table>
      <thead><tr><th>Port</th><th>Service</th><th>Max CVSS</th><th>Top CVE</th><th>Risks</th></tr></thead>
      <tbody>{cve_rows}</tbody>
    </table>
  </div>'''}

  {"" if not cred_rows else f'''
  <div style="padding:0 16px 12px">
    <h4 style="margin:0 0 8px;color:#8e44ad">Default Credential Risk</h4>
    <table>
      <thead><tr><th>Port</th><th>Protocol</th><th>Entries</th><th>Sample credentials</th></tr></thead>
      <tbody>{cred_rows}</tbody>
    </table>
  </div>'''}

  {"<div style='padding:12px 16px;color:#27ae60'>✅ No CVE or default credential matches for open ports.</div>" if not cve_rows and not cred_rows else ""}
</div>"""

def render_html(reports: list[dict]) -> str:
    generated = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    total_critical = sum(
        1 for r in reports
        for info in r.get("cve_hits", {}).values()
        if isinstance(info, dict) and info.get("max", info.get("max_cvss", 0)) >= 9.0
    )
    cards = "\n".join(render_scan_card(r) for r in reports)
    targets = len({r.get("target") for r in reports})

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>hacker-tool · Dashboard</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, monospace;
    background: #0d1117; color: #e6edf3; font-size: 14px; line-height: 1.5;
  }}
  header {{
    background: #161b22; border-bottom: 1px solid #30363d;
    padding: 16px 24px; position: sticky; top: 0; z-index: 10;
  }}
  header h1 {{ font-size: 1.2em; color: #58a6ff; }}
  header .meta {{ color: #8b949e; font-size: 0.8em; margin-top: 4px; }}
  .stats {{
    display: flex; gap: 16px; flex-wrap: wrap;
    padding: 16px 24px; background: #0d1117; border-bottom: 1px solid #21262d;
  }}
  .stat-box {{
    background: #161b22; border: 1px solid #30363d; border-radius: 8px;
    padding: 12px 20px; min-width: 120px; text-align: center;
  }}
  .stat-box .num {{ font-size: 2em; font-weight: bold; }}
  .stat-box .lbl {{ color: #8b949e; font-size: 0.8em; text-transform: uppercase; }}
  main {{ padding: 24px; max-width: 1100px; margin: 0 auto; }}
  .card {{
    background: #161b22; border: 1px solid #30363d; border-radius: 8px;
    overflow: hidden;
  }}
  table {{ width: 100%; border-collapse: collapse; font-size: 0.9em; }}
  th {{ background: #21262d; padding: 8px 10px; text-align: left; color: #8b949e;
        font-weight: 600; text-transform: uppercase; font-size: 0.75em; }}
  td {{ padding: 8px 10px; border-top: 1px solid #21262d; vertical-align: top; }}
  tr:hover td {{ background: #1c2128; }}
  code {{ background: #21262d; padding: 1px 5px; border-radius: 3px;
          font-family: monospace; font-size: 0.9em; }}
  .badge {{
    display: inline-block; padding: 2px 9px; border-radius: 12px;
    font-size: 0.8em; font-weight: 600; color: #fff; margin-left: 6px;
  }}
  h4 {{ color: #e6edf3; font-size: 0.95em; }}
  .empty {{ text-align: center; padding: 60px; color: #8b949e; }}
  footer {{ text-align: center; color: #484f58; padding: 32px; font-size: 0.8em; }}
</style>
</head>
<body>

<header>
  <h1>⚡ hacker-tool · Security Dashboard</h1>
  <div class="meta">Generated {generated} &nbsp;·&nbsp; {len(reports)} scan(s) &nbsp;·&nbsp; {targets} target(s)</div>
</header>

<div class="stats">
  <div class="stat-box">
    <div class="num" style="color:#58a6ff">{len(reports)}</div>
    <div class="lbl">Scans</div>
  </div>
  <div class="stat-box">
    <div class="num" style="color:#58a6ff">{targets}</div>
    <div class="lbl">Targets</div>
  </div>
  <div class="stat-box">
    <div class="num" style="color:#c0392b">{total_critical}</div>
    <div class="lbl">Critical CVEs</div>
  </div>
  <div class="stat-box">
    <div class="num" style="color:#e67e22">{sum(len(r.get("cve_hits",{})) for r in reports)}</div>
    <div class="lbl">CVE matches</div>
  </div>
  <div class="stat-box">
    <div class="num" style="color:#8e44ad">{sum(len(r.get("cred_hits",{})) for r in reports)}</div>
    <div class="lbl">Cred risks</div>
  </div>
  <div class="stat-box">
    <div class="num" style="color:#27ae60">{sum(len(r.get("open_ports",[])) for r in reports)}</div>
    <div class="lbl">Open ports</div>
  </div>
</div>

<main>
{"".join([f'<div class="empty">📭 No pipeline reports found.<br>Run: <code>hackertool net pipeline gateway --save</code></div>']) if not reports else cards}
</main>

<footer>hacker-tool &nbsp;·&nbsp; generated {generated} &nbsp;·&nbsp; offline</footer>
</body>
</html>"""

def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    do_open = "--open" in argv
    specific = [a for a in argv if not a.startswith("--") and a]

    REPORTS_DIR.mkdir(exist_ok=True)

    if specific:
        files = [Path(f) for f in specific if Path(f).exists()]
    else:
        files = sorted(REPORTS_DIR.glob("pipeline_*.json"), reverse=True)

    reports = load_reports(files)
    html    = render_html(reports)
    OUT_FILE.write_text(html)

    print(f"Dashboard generated → {OUT_FILE}")
    print(f"  Scans: {len(reports)}  |  "
          f"Critical CVEs: {sum(1 for r in reports for i in r.get('cve_hits',{}).values() if isinstance(i,dict) and i.get('max',0)>=9)}")

    if do_open:
        import subprocess
        try:
            subprocess.run(["termux-open", str(OUT_FILE)], timeout=5)
            print("  Opened in browser.")
        except Exception as e:
            print(f"  termux-open failed: {e}")
            print(f"  Manual: termux-open {OUT_FILE}")

    return 0

if __name__ == "__main__":
    sys.exit(main())
