"""Chia tap theo thoi gian, tia bot cot, va scale co tham so.

Ranh gioi ro ri du lieu nam o day. Moi thu trong base.py / indicators.py deu la
phep bien doi nhan qua khong tham so. Nguoc lai, module nay *uoc luong* tham so
(trung vi, IQR, danh sach cot bi loai) - nen tat ca chi duoc tinh tren tap train.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from .config import FeatureConfig


@dataclass
class TimeSplit:
    """Mat na train/valid/test theo thoi gian, co vung dem (embargo)."""

    train: np.ndarray
    valid: np.ndarray
    test: np.ndarray
    index: pd.DatetimeIndex

    def summary(self) -> str:
        rows = []
        for name in ("train", "valid", "test"):
            m = getattr(self, name)
            if not m.any():
                rows.append(f"{name:6s} rong")
                continue
            i = self.index[m]
            rows.append(f"{name:6s} {m.sum():7d} bar  {i[0].date()} -> {i[-1].date()}")
        return "\n".join(rows)


def make_split(index: pd.DatetimeIndex, cfg: FeatureConfig) -> TimeSplit:
    """Chia theo moc thoi gian, khong xao tron.

    Vung embargo bo `embargo_bars` ngay sau moi moc: dac trung cua so dai va nhan
    nhin toi tuong lai deu lam hai bar canh ranh gioi chong lan nhau. Khong co
    embargo thi diem valid dau tien van "biet" ve cac bar train cuoi cung.
    """
    train_end = pd.Timestamp(cfg.train_end) + pd.Timedelta(days=1)
    valid_end = pd.Timestamp(cfg.valid_end) + pd.Timedelta(days=1)

    train = np.asarray(index < train_end)
    valid = np.asarray((index >= train_end) & (index < valid_end))
    test = np.asarray(index >= valid_end)

    e = cfg.embargo_bars
    if e > 0:
        for mask in (valid, test):
            first = np.argmax(mask) if mask.any() else 0
            mask[first:first + e] = False
    return TimeSplit(train, valid, test, index)


@dataclass
class FeatureScaler:
    """Scale robust (trung vi / IQR) khop rieng tren tap train.

    Dung robust thay vi trung binh/do lech chuan vi phan phoi loi nhuan tai chinh
    co duoi rat day: mot phien sap san se keo lech do lech chuan va nen toan bo
    cac gia tri con lai ve gan 0.
    """

    columns: list[str] = field(default_factory=list)
    center: np.ndarray | None = None
    scale: np.ndarray | None = None
    clip: float = 8.0
    mode: str = "robust"

    def fit(self, df: pd.DataFrame, mask: np.ndarray) -> "FeatureScaler":
        train = df.to_numpy(dtype="float64")[mask]
        self.columns = list(df.columns)
        if self.mode == "none":
            self.center = np.zeros(train.shape[1])
            self.scale = np.ones(train.shape[1])
            return self
        if self.mode == "standard":
            center = np.nanmean(train, axis=0)
            scale = np.nanstd(train, axis=0)
        else:
            q25, center, q75 = np.nanpercentile(train, [25, 50, 75], axis=0)
            scale = (q75 - q25) / 1.349          # quy ve don vi sigma cua phan phoi chuan
        # Cot gan nhu hang so (vi du mau nen hiem) co IQR = 0; giu nguyen thay vi
        # chia cho 0 va bien chung thanh inf.
        scale = np.where(np.isfinite(scale) & (scale > 1e-9), scale, 1.0)
        self.center = np.nan_to_num(center)
        self.scale = scale
        return self

    def transform(self, df: pd.DataFrame) -> np.ndarray:
        if self.center is None:
            raise RuntimeError("scaler chua duoc fit")
        x = (df[self.columns].to_numpy(dtype="float64") - self.center) / self.scale
        np.clip(x, -self.clip, self.clip, out=x)
        # NaN con sot lai (bar khoi dong, mau so bang 0) -> 0 = trung vi tap train.
        return np.nan_to_num(x, nan=0.0, posinf=self.clip, neginf=-self.clip).astype("float32")

    def save(self, path: str | Path) -> None:
        path = Path(path)
        np.savez_compressed(path, center=self.center, scale=self.scale)
        path.with_suffix(".json").write_text(
            json.dumps({"columns": self.columns, "clip": self.clip, "mode": self.mode}),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: str | Path) -> "FeatureScaler":
        path = Path(path)
        meta = json.loads(path.with_suffix(".json").read_text(encoding="utf-8"))
        z = np.load(path.with_suffix(".npz"))
        return cls(meta["columns"], z["center"], z["scale"], meta["clip"], meta["mode"])


def prune_columns(
    df: pd.DataFrame,
    mask: np.ndarray,
    min_unique_frac: float = 1e-4,
    corr_threshold: float = 0.999,
) -> tuple[list[str], dict[str, str]]:
    """Loai cot chet va cot trung lap, chi dua tren tap train.

    Tra ve (cot giu lai, ly do loai). Hai nhom bi loai:
      - gan nhu hang so: vi du CDL3STARSINSOUTH khong xuat hien lan nao trong 9 nam;
      - trung lap: |corr| >= nguong, vi du ofi tinh theo khoi luong va theo gia tri.
    Voi mang neural chung khong gay hai truc tiep nhung lam tang so chieu va lam
    nhieu moi phan tich do quan trong dac trung ve sau.
    """
    train = df.iloc[mask]
    keep: list[str] = []
    dropped: dict[str, str] = {}

    active = (train.ne(0) & train.notna()).mean()
    variance = train.var(numeric_only=True)
    for c in df.columns:
        if not np.isfinite(variance.get(c, np.nan)) or variance.get(c, 0.0) <= 0:
            dropped[c] = "hang so"
        elif active.get(c, 1.0) < min_unique_frac:
            dropped[c] = f"gan nhu luon bang 0 ({active[c]:.5f})"
        else:
            keep.append(c)

    sub = train[keep].to_numpy(dtype="float32")
    corr = np.corrcoef(np.nan_to_num(sub), rowvar=False)
    corr = np.nan_to_num(corr)
    survivors: list[str] = []
    surv_idx: list[int] = []                 # giu chi so de tranh tim tuyen tinh trong vong lap
    for j, c in enumerate(keep):
        if surv_idx:
            sim = np.abs(corr[j, surv_idx])
            k = int(np.argmax(sim))
            if sim[k] >= corr_threshold:
                dropped[c] = f"trung lap voi {survivors[k]}"
                continue
        survivors.append(c)
        surv_idx.append(j)
    return survivors, dropped
