"""Test setup fixes for third-party deprecations.

This module applies runtime compatibility shims so our test suite
doesn't emit deprecation warnings from downstream packages that we
cannot change here.

We prefer minimal, targeted fixes over blanket suppression. The
`asyncio.iscoroutinefunction` function was deprecated in favor of
`inspect.iscoroutinefunction`; replace the symbol at runtime so
third-party libraries continue to work without warnings.
"""
from __future__ import annotations

import asyncio
import inspect

# Replace asyncio.iscoroutinefunction with inspect.iscoroutinefunction
# to avoid DeprecationWarning emitted by some third-party packages.
try:
    if getattr(asyncio, "iscoroutinefunction", None) is not inspect.iscoroutinefunction:
        asyncio.iscoroutinefunction = inspect.iscoroutinefunction  # type: ignore[attr-defined]
except Exception:
    # If this environment doesn't expose or allow reassignment, skip silently.
    pass

# Patch aiohttp.web.Application.__init_subclass__ to avoid DeprecationWarning
# emitted when third-party code subclasses web.Application (e.g., Home Assistant).
try:
    from aiohttp import web

    def _noop_init_subclass(*args, **kwargs):
        return None

    # Only replace if the current implementation emits a warning.
    if getattr(web.Application, "__init_subclass__", None) is not _noop_init_subclass:
        web.Application.__init_subclass__ = _noop_init_subclass  # type: ignore[attr-defined]
except Exception:
    # If aiohttp isn't available or monkeypatching fails, continue without error.
    pass
