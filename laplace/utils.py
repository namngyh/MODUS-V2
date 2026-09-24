"""Ham tien ich dung chung."""

from __future__ import annotations

import numpy as np
import pandas as pd

EPS = 1e-12


def safe_div(a, b, fill: float = 0.0):
    """Chia co bao ve: mau bang 0 (bar phang H==L) tra ve `fill` thay vi inf."""
    a = np.asarray(a, dtype="float64")
    b = np.asarray(b, dtype="float64")
    out = np.full(a.shape, fill, dtype="float64")
    ok = np.abs(b) > EPS
    np.divide(a, b, out=out, where=ok)
    return out


def safe_log(a):
    a = np.asarray(a, dtype="float64")
    return np.log(np.where(a > EPS, a, np.nan))


def log_ratio(a, b):
    """log(a/b) - dang chuan de bien muc gia thanh dai luong khong thu nguyen."""
    return safe_log(a) - safe_log(b)


def causal_seasonal_mean(values: pd.Series, key: pd.Series, lookback: int = 60) -> pd.Series:
    """Trung binh truot theo nhom, da dich 1 buoc.

    Dung de khu mua vu trong phien: khoi luong bar 09:00 luon lon hon bar 11:20,
    nen phai so voi trung binh lich su cua *chinh bar do*. Shift(1) dam bao quan sat
    hien tai khong tham gia vao trung binh cua chinh no. Dung cua so truot
    (`lookback` phien) chu khong phai luy tien, vi khoi luong tang truong nhieu lan
    qua 9 nam - trung binh luy tien se lech he thong.
    """
    grp = values.groupby(key, sort=False)
    return grp.transform(lambda s: s.shift(1).rolling(lookback, min_periods=10).mean())


def prefix(df: pd.DataFrame, tag: str) -> pd.DataFrame:
    df.columns = [f"{tag}__{c}" for c in df.columns]
    return df
