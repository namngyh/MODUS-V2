"""Cac ham co ban cua AmiBroker Formula Language, viet lai bang numpy.

Hai bot trong bot/ duoc viet bang AFL. De tai lap dung tin hieu cua chung trong
Python can dung ngu nghia AFL - dac biet la Flip va ExRem, hai may trang thai ma
pandas khong co san. Moi ham o day deu nhan qua: gia tri tai i chi phu thuoc cac
phan tu <= i.
"""

from __future__ import annotations

import numpy as np
import talib


def cross(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """AFL Cross(a, b): a cat len tren b tai bar nay."""
    a = np.asarray(a, dtype="float64")
    b = np.asarray(b, dtype="float64")
    now = a > b
    prev = np.empty_like(now)
    prev[0] = False
    prev[1:] = a[:-1] <= b[:-1]
    return now & prev


def flip(on: np.ndarray, off: np.ndarray) -> np.ndarray:
    """AFL Flip(on, off): giu trang thai 1 tu tin hieu `on` cho toi khi `off`.

    Khi ca hai cung bat tren mot bar, `on` thang - dung nhu AmiBroker.
    """
    on = np.asarray(on, dtype=bool)
    off = np.asarray(off, dtype=bool)
    out = np.zeros(len(on), dtype=bool)
    state = False
    for i in range(len(on)):
        if on[i]:
            state = True
        elif off[i]:
            state = False
        out[i] = state
    return out


def exrem(sig: np.ndarray, reset: np.ndarray) -> np.ndarray:
    """AFL ExRem(sig, reset): chi giu tin hieu `sig` dau tien sau moi `reset`."""
    sig = np.asarray(sig, dtype=bool)
    reset = np.asarray(reset, dtype=bool)
    out = np.zeros(len(sig), dtype=bool)
    armed = True
    for i in range(len(sig)):
        if reset[i]:
            armed = True
        if sig[i] and armed:
            out[i] = True
            armed = False
    return out


def ref(a: np.ndarray, shift: int) -> np.ndarray:
    """AFL Ref(a, -n): lay gia tri cua n bar truoc. Chi ho tro shift am (nhan qua)."""
    if shift > 0:
        raise ValueError("Ref voi shift duong la nhin truoc tuong lai")
    a = np.asarray(a, dtype="float64")
    out = np.full_like(a, np.nan)
    n = -shift
    if n == 0:
        return a.copy()
    out[n:] = a[:-n]
    return out


def hhv(a: np.ndarray, periods: int) -> np.ndarray:
    return talib.MAX(np.asarray(a, dtype="float64"), timeperiod=periods)


def llv(a: np.ndarray, periods: int) -> np.ndarray:
    return talib.MIN(np.asarray(a, dtype="float64"), timeperiod=periods)


def stoch_k(high, low, close, periods: int, ksmooth: int) -> np.ndarray:
    """AFL StochK(periods, ksmooth): %K tho roi lam muot bang SMA.

    Khong dung talib.STOCH duoc vi tham so o day (22, 43) khac han cau hinh
    fastk/slowk thong thuong, va AmiBroker lam muot bang SMA.
    """
    high = np.asarray(high, dtype="float64")
    low = np.asarray(low, dtype="float64")
    close = np.asarray(close, dtype="float64")
    hi = hhv(high, periods)
    lo = llv(low, periods)
    rng = hi - lo
    raw = np.full_like(close, np.nan)
    ok = rng > 1e-12
    raw[ok] = 100.0 * (close[ok] - lo[ok]) / rng[ok]
    raw[~ok & np.isfinite(hi)] = 50.0        # bar phang: khong co thong tin vi tri
    return talib.SMA(raw, timeperiod=ksmooth)


def position_from_signals(
    buy: np.ndarray, sell: np.ndarray, short: np.ndarray, cover: np.ndarray
) -> np.ndarray:
    """Mo phong trang thai vi the cua backtester AmiBroker.

    Thu tu trong mot bar: dong lenh truoc, mo lenh sau - nho vay tin hieu dao chieu
    (Sell va Short cung bat) dong vi the cu roi mo vi the moi ngay trong bar do.
    Ca hai bot deu dat SetTradeDelays(0,...) hoac vao lenh tai Close cua bar tin
    hieu, nen vi the tai bar i da co hieu luc tu cuoi bar i.
    """
    buy = np.asarray(buy, dtype=bool)
    sell = np.asarray(sell, dtype=bool)
    short = np.asarray(short, dtype=bool)
    cover = np.asarray(cover, dtype=bool)

    out = np.zeros(len(buy), dtype="int8")
    pos = 0
    for i in range(len(buy)):
        if pos == 1 and sell[i]:
            pos = 0
        elif pos == -1 and cover[i]:
            pos = 0
        if pos == 0:
            if buy[i]:
                pos = 1
            elif short[i]:
                pos = -1
        out[i] = pos
    return out
