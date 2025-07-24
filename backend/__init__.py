"""Backend package initialization with basic logging configuration."""

from __future__ import annotations

import logging

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
