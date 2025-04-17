from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DefaultFactory:
    pyfunc: str
    tsfunc: str
