"""
modules/report/generate.py — turn any dict/list result into a Markdown
(and optionally HTML) report.
"""
from datetime import datetime, timezone
import json
from pathlib import Path


def _to_markdown(title: str, data) -> str:
    lines = [f"# {title}", "", f"_Generated: {datetime.now(timezone.utc).isoformat()}_", ""]
    lines.append("```json")
    lines.append(json.dumps(data, indent=2))
    lines.append("```")
    return "\n".join(lines)


def write_report(title: str, data, out_dir: Path, name: str = "report", fmt: str = "md") -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    md = _to_markdown(title, data)

    if fmt == "md":
        out_path = out_dir / f"{name}_{ts}.md"
        out_path.write_text(md)
    elif fmt == "html":
        out_path = out_dir / f"{name}_{ts}.html"
        html = f"<html><head><meta charset='utf-8'><title>{title}</title></head><body><pre>{md}</pre></body></html>"
        out_path.write_text(html)
    else:
        raise ValueError(f"Unknown format: {fmt}")

    return out_path
