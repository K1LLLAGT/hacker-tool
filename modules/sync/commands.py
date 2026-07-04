"""
modules/sync/commands.py — push/pull/status against SMB or path-based remote.
"""
from core.storage import Storage


def cmd_push(cfg, logger, name: str):
    Storage(cfg, logger).push(name)


def cmd_pull(cfg, logger, name: str):
    Storage(cfg, logger).pull(name)


def cmd_status(cfg, logger, name: str) -> dict:
    return Storage(cfg, logger).status(name)
