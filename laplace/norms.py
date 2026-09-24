"""Chuan hoa dau ra indicator ve dang khong thu nguyen, dung phan phoi on dinh.

Day la phan quan trong nhat cua pipeline. TA-Lib tra ve gia tri o rat nhieu don vi
khac nhau: SMA la muc gia (~1900), RSI la 0..100, WILLR la -100..0, OBV la tong
tich luy tang vo han, LINEARREG_ANGLE la do. Nem thang tat ca vao mang neural la
cach chac chan nhat de mo hinh khong hoc duoc gi.

Moi output duoc gan mot "kieu" mo ta don vi cua no; ham tuong ung o day bien no ve
thang do so sanh duoc, *khong dung tham so nao uoc luong tu du lieu* (nen khong
the ro ri thong tin tuong lai). Buoc scale cuoi cung - co tham so - nam o scaling.py
va chi khop tren tap train.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .utils import EPS, safe_div, safe_log


@dataclass
class NormContext:
    """Cac chuoi tham chieu de quy doi don vi."""

    close: np.ndarray
    volume: np.ndarray
    vol_ma: np.ndarray          # khoi luong trung binh truot, mau so cho chi bao dong tien
    index: pd.DatetimeIndex


def _price(x, ctx):
    """Muc gia -> log(x / close). 0 nghia la indicator trung gia hien tai."""
    return safe_log(x) - safe_log(ctx.close)


def _absprice(x, ctx):
    """Muc gia co the mang dau (SAREXT dung dau de bao chieu vi the).

    log(|x| / close) giu lai khoang cach den gia; chieu duoc tach ra thanh cot
    rieng bang kieu "sign", neu khong 48% so bar se thanh NaN.
    """
    return safe_log(np.abs(x)) - safe_log(ctx.close)


def _sign(x, ctx):
    return np.sign(x)


def _pdiff(x, ctx):
    """Chenh lech / do phan tan tinh bang don vi gia -> ty le tren gia."""
    return safe_div(x, ctx.close)


def _pvar(x, ctx):
    """Phuong sai (gia^2) -> do lech chuan tren gia."""
    return safe_div(np.sqrt(np.clip(x, 0.0, None)), ctx.close)


def _pct100(x, ctx):
    """Dao dong 0..100 -> -1..1."""
    return x / 50.0 - 1.0


def _pct100n(x, ctx):
    """Dao dong -100..0 (WILLR) -> -1..1."""
    return x / 50.0 + 1.0


def _signed100(x, ctx):
    """Dao dong -100..100, va tin hieu nen (-100/0/100) -> -1..1."""
    return x / 100.0


def _pct(x, ctx):
    """Gia tri da o don vi phan tram (ROC, NATR, TRIX, PPO) -> ty le."""
    return x / 100.0


def _deg(scale):
    def f(x, ctx):
        return x / scale
    return f


def _dcperiod(x, ctx):
    """Chu ky troi Hilbert nam trong khoang ~6..50 bar; dua ve quanh 0."""
    return (x - 27.0) / 20.0


def _flow(x, ctx):
    """Chi bao dong tien tinh bang don vi khoi luong -> chia cho khoi luong trung binh."""
    return safe_div(x, ctx.vol_ma)


def _flow_diff(x, ctx):
    """Chuoi tich luy (AD, OBV): lay sai phan truoc roi moi chuan hoa.

    OBV chay tu 2017 den nay la mot chuoi khong dung, muc cua no chi phan anh
    diem bat dau tinh toan. Chi co bien thien moi mang thong tin.
    """
    d = np.diff(x, prepend=np.nan)
    return safe_div(d, ctx.vol_ma)


def _identity(x, ctx):
    return np.asarray(x, dtype="float64")


NORMS = {
    "price": _price,
    "absprice": _absprice,
    "sign": _sign,
    "pdiff": _pdiff,
    "pvar": _pvar,
    "pct100": _pct100,
    "pct100n": _pct100n,
    "signed100": _signed100,
    "pct": _pct,
    "deg90": _deg(90.0),
    "deg180": _deg(180.0),
    "div100": _deg(100.0),      # CCI: khong chan nhung do lon dien hinh la +-100..200
    "dcperiod": _dcperiod,
    "flow": _flow,
    "flow_diff": _flow_diff,
    "pass": _identity,
}


def apply_norm(kind: str, x: np.ndarray, ctx: NormContext) -> np.ndarray:
    try:
        fn = NORMS[kind]
    except KeyError:
        raise KeyError(f"kieu chuan hoa khong biet: {kind!r}") from None
    return fn(np.asarray(x, dtype="float64"), ctx)


def make_context(df: pd.DataFrame, vol_window: int = 255) -> NormContext:
    vol_ma = (
        df["volume"].rolling(vol_window, min_periods=20).mean().bfill().to_numpy(dtype="float64")
    )
    return NormContext(
        close=df["close"].to_numpy(dtype="float64"),
        volume=df["volume"].to_numpy(dtype="float64"),
        vol_ma=np.where(vol_ma > EPS, vol_ma, 1.0),
        index=df.index,
    )
