"""Ghep toan bo cac nhom dac trung thanh mot ma tran san sang cho mo hinh."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .base import build_base
from .bots import BotRun, build_bot_features, build_bot_signals, run_kespt, run_roofing
from .config import FeatureConfig
from .indicators import build_group
from .loader import load_ohlcv
from .norms import make_context
from .orderflow import build_orderflow
from .scaling import FeatureScaler, TimeSplit, make_split, prune_columns
from .session import build_session
from .stationarity import stationarize

# Anh xa co giao tu nhom nguoi dung yeu cau sang builder tuong ung.
TALIB_GROUPS = {
    "use_candles": "candles",
    "use_cycles": "cycles",
    "use_momentum": "momentum",
    "use_overlap": "overlap",
    "use_statistic": "statistic",
    "use_volatility": "volatility",
    "use_volume": "volume",
}


@dataclass
class FeatureSet:
    """Ket qua cuoi cung: ma tran dac trung + moi thu can de tai lap."""

    features: pd.DataFrame          # da chuan hoa don vi, chua scale
    ohlcv: pd.DataFrame             # bar goc, can cho backtest va sinh nhan
    split: TimeSplit
    scaler: FeatureScaler
    dropped: dict[str, str] = field(default_factory=dict)
    burn_in: int = 0
    groups: dict[str, list[str]] = field(default_factory=dict)
    # Quyet dinh cua hai bot AFL, {-1, 0, 1}. KHONG nam trong `features` va khong
    # di qua scaler: day la y kien tham chieu de agent doi chieu, khong phai dau vao.
    signals: pd.DataFrame | None = None

    @property
    def columns(self) -> list[str]:
        return list(self.features.columns)

    def matrix(self) -> np.ndarray:
        """Ma tran (T, F) float32 da scale - dau vao truc tiep cua mo hinh."""
        return self.scaler.transform(self.features)

    def report(self) -> str:
        lines = [
            f"bar          : {len(self.features):,}",
            f"dac trung    : {len(self.columns)}  (loai {len(self.dropped)})",
            f"burn-in      : {self.burn_in} bar dau bi cat",
            "",
            "So cot theo nhom:",
        ]
        lines += [f"  {g:12s} {len(c):4d}" for g, c in self.groups.items()]
        if self.signals is not None:
            lines += ["", "Tin hieu bot (khong phai dac trung):"]
            for bot in ("kespt", "roofing", "both"):
                pos = self.signals[f"{bot}_pos"]
                lines.append(
                    f"  {bot:8s} long {(pos == 1).sum():6d}  short {(pos == -1).sum():6d}"
                    f"  flat {(pos == 0).sum():6d}"
                    f"   ({(pos != 0).mean():.1%} thoi gian co vi the)"
                )
        lines += ["", self.split.summary()]
        return "\n".join(lines)


def run_bots(df: pd.DataFrame) -> dict[str, BotRun]:
    """Chay hai bot AFL mot lan; ket qua dung cho ca dac trung lan tin hieu."""
    return {"kespt": run_kespt(df), "roofing": run_roofing(df)}


def build_raw_features(df: pd.DataFrame, cfg: FeatureConfig,
                       runs: dict[str, BotRun] | None = None) -> dict[str, pd.DataFrame]:
    """Tinh tung nhom rieng le, chua ghep - de kiem tra hoac dung le tung nhom."""
    ctx = make_context(df, vol_window=cfg.vol_windows[-1])
    blocks: dict[str, pd.DataFrame] = {}

    if cfg.use_base:
        blocks["base"] = build_base(df, cfg)
    for flag, group in TALIB_GROUPS.items():
        if getattr(cfg, flag):
            blocks[group] = build_group(group, df, cfg, ctx)
    if cfg.use_overlap:
        # Price transform di kem nhom overlap: cung la cac muc gia phai sinh.
        blocks["price"] = build_group("price", df, cfg, ctx)
    if cfg.use_orderflow:
        blocks["flow"] = build_orderflow(df, cfg)
    if cfg.use_session:
        blocks["session"] = build_session(df, cfg)
    if cfg.use_bots:
        blocks["bot"] = build_bot_features(df, cfg, runs or run_bots(df))
    if cfg.stationarize:
        # Dat o day chu khong o build_feature_frame de bai kiem tra nhan qua (bat bien
        # #2), von goi ham nay, phu luon buoc bien doi theo lop.
        blocks = {g: stationarize(b, cfg) for g, b in blocks.items()}
    return blocks


def _burn_in_length(features: pd.DataFrame) -> int:
    """So bar dau tien phai cat bo.

    Indicator cham nhat quyet dinh: T3 chu ky 255 can 6x254 bar moi cho gia tri
    dau tien. Giu lai cac bar do se nhoi NaN (roi thanh 0 sau khi scale) vao dung
    doan du lieu som nhat, va mo hinh se hoc tren mot the gioi khong ton tai.
    """
    first_valid = [features[c].first_valid_index() for c in features.columns]
    first_valid = [f for f in first_valid if f is not None]
    if not first_valid:
        return 0
    return int(features.index.get_indexer([max(first_valid)])[0]) + 1


def build_feature_frame(cfg: FeatureConfig | None = None,
                        df: pd.DataFrame | None = None) -> FeatureSet:
    """Duong ong day du: CSV tho -> FeatureSet da chia tap va khop scaler."""
    cfg = cfg or FeatureConfig()
    df = load_ohlcv(cfg) if df is None else df

    runs = run_bots(df) if (cfg.use_bots or cfg.emit_bot_signals) else None
    blocks = build_raw_features(df, cfg, runs)
    features = pd.concat(blocks.values(), axis=1)

    signals = build_bot_signals(df, runs) if cfg.emit_bot_signals else None

    burn_in = _burn_in_length(features)
    features = features.iloc[burn_in:]
    ohlcv = df.iloc[burn_in:]
    if signals is not None:
        signals = signals.iloc[burn_in:]

    split = make_split(features.index, cfg)
    if not split.train.any():
        raise ValueError(
            f"tap train rong: train_end={cfg.train_end} nam truoc bar dau tien "
            f"sau burn-in ({features.index[0].date()})"
        )

    keep, dropped = prune_columns(features, split.train)
    features = features[keep]

    scaler = FeatureScaler(clip=cfg.clip_sigma, mode=cfg.scaler).fit(features, split.train)

    groups = {
        g: [c for c in features.columns if c.startswith(f"{g}__")] for g in blocks
    }
    return FeatureSet(features, ohlcv, split, scaler, dropped, burn_in, groups, signals)
