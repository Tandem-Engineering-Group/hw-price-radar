"""Lot record schema. PascalCase fields throughout (repo convention)."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field, asdict
from typing import Optional

VALID_STATUS = {"Active", "Pending", "Sold", "Delisted"}
VALID_FACING = {"N", "NE", "E", "SE", "S", "SW", "W", "NW"}
VALID_UTILITIES_BAND = {"Full", "Partial", "None"}
VALID_LEVEL_BAND = {"High", "Med", "Low"}


def lot_id(source_url: str) -> str:
    return hashlib.sha1(source_url.strip().lower().encode()).hexdigest()[:12]


@dataclass
class Lot:
    LotId: str
    Source: str
    SourceUrl: str
    Lat: float
    Lon: float
    Status: str = "Active"
    FirstSeen: Optional[str] = None
    LastSeen: Optional[str] = None
    PriceUsd: Optional[int] = None
    PriceHistory: list = field(default_factory=list)
    AcreageAc: Optional[float] = None
    FrontageFt: Optional[float] = None
    LakeName: Optional[str] = None
    LakeTier: Optional[str] = None
    County: Optional[str] = None
    Township: Optional[str] = None
    RoadElevationFt: Optional[float] = None
    ShoreElevationFt: Optional[float] = None
    GradeFallFt: Optional[float] = None
    ShoreFacing: Optional[str] = None
    DriveMinsFromDetroit: Optional[int] = None
    Name: Optional[str] = None
    Utilities: Optional[str] = None
    UtilitiesBand: Optional[str] = None
    GrowthBand: Optional[str] = None
    TaxBand: Optional[str] = None
    LastVerified: Optional[str] = None
    Scores: dict = field(default_factory=dict)
    Flags: list = field(default_factory=list)
    Notes: str = ""
    Placeholder: bool = False

    def validate(self) -> list[str]:
        problems = []
        if self.Status not in VALID_STATUS:
            problems.append(f"Status '{self.Status}' invalid")
        if self.ShoreFacing and self.ShoreFacing not in VALID_FACING:
            problems.append(f"ShoreFacing '{self.ShoreFacing}' invalid")
        if not (-90 <= self.Lat <= 90 and -180 <= self.Lon <= 180):
            problems.append("Lat/Lon out of range")
        if self.UtilitiesBand and self.UtilitiesBand not in VALID_UTILITIES_BAND:
            problems.append(f"UtilitiesBand '{self.UtilitiesBand}' invalid")
        for name in ("GrowthBand", "TaxBand"):
            val = getattr(self, name)
            if val and val not in VALID_LEVEL_BAND:
                problems.append(f"{name} '{val}' invalid")
        return problems

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_watchlist(cls, entry: dict) -> "Lot":
        url = entry["SourceUrl"]
        known = {f for f in cls.__dataclass_fields__}
        clean = {k: v for k, v in entry.items() if k in known}
        clean.setdefault("Source", "watchlist")
        clean["LotId"] = lot_id(url)
        return cls(**clean)
