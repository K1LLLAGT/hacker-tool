"""
core/logging_setup.py — Unified logging, writes to console + local_root/data/hacker-tool.log
"""
import logging
from pathlib import Path


def setup_logging(cfg: dict) -> logging.Logger:
    logger = logging.getLogger("hacker-tool")
    if logger.handlers:
        return logger  # already configured (idempotent for module reuse)

    level = getattr(logging, str(cfg.get("log_level", "INFO")).upper(), logging.INFO)
    logger.setLevel(level)

    log_path = Path(cfg["local_root"]) / "data" / "hacker-tool.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    fh = logging.FileHandler(log_path)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(ch)

    return logger
