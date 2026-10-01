"""Nhan cho LSTM du bao (spec 008): gia cham moc tren hay moc duoi truoc.

Quy uoc khop voi profit (CLAUDE.md muc 9): quyet dinh o cuoi nen t, VAO LENH o gia mo cua
nen t+1. Moc = gia vao +- k * ATR(t). Quet cac nen t+1 .. het, voi
    het = min(t + horizon, nen cuoi cung cua phien chua t)
- khong bao gio quet sang phien sau: cu nhay gia qua dem (trung binh 3,9 diem tren train,
khoang 2,6 ATR) se quyet dinh nhan thay cho dien bien trong phien.

Nhan CO Y nhin tuong lai toi nen `het`. Moi noi dung nhan phai cat bo (purge) nhung nen co
`het` cham vao giai doan khong duoc phep thay - xem folds.py.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import talib

DOWN, FLAT, UP = 0, 1, 2          # chi so lop cua head (a)
NO_LABEL = -1


@dataclass
class BarrierLabels:
    label: np.ndarray      # (T,) int8: DOWN / FLAT / UP, NO_LABEL neu khong co nhan
    ret_atr: np.ndarray    # (T,) float: (dong cua nen het - gia vao) / ATR - dap an head (c)
    end: np.ndarray        # (T,) int: nen cuoi cung ma nhan nhin toi (de purge)
    atr: np.ndarray        # (T,) float: ATR tai t, don vi diem

    @property
    def valid(self) -> np.ndarray:
        return self.label != NO_LABEL


def barrier_labels(open_: np.ndarray, high: np.ndarray, low: np.ndarray, close: np.ndarray,
                   session: np.ndarray, atr: np.ndarray, k: float, horizon: int) -> BarrierLabels:
    """Tinh nhan vector hoa theo t; chi vong lap tren `horizon` buoc nhin truoc."""
    n = len(close)
    t = np.arange(n)
    nxt = np.minimum(t + 1, n - 1)

    # Nen cuoi cua phien chua t: mot luot quet nguoc
    last_in_session = np.empty(n, dtype=np.int64)
    last = n - 1
    for i in range(n - 1, -1, -1):
        if i < n - 1 and session[i] != session[i + 1]:
            last = i
        last_in_session[i] = last
    end = np.minimum(t + horizon, last_in_session)

    ok = (t + 1 < n) & (session[nxt] == session) & np.isfinite(atr) & (atr > 0)
    entry = open_[nxt]
    up_lv, dn_lv = entry + k * atr, entry - k * atr

    label = np.full(n, NO_LABEL, dtype=np.int8)
    label[ok] = FLAT
    undecided = ok.copy()
    for j in range(1, horizon + 1):
        idx = np.minimum(t + j, n - 1)
        live = undecided & (t + j <= end)
        hit_up = live & (high[idx] >= up_lv)
        hit_dn = live & (low[idx] <= dn_lv)
        both = hit_up & hit_dn
        # Cung mot nen cham ca hai moc: khong biet cai nao truoc trong nen -> phan xu bang
        # gia dong cua nen do so voi gia vao.
        up_win = (hit_up & ~hit_dn) | (both & (close[idx] >= entry))
        dn_win = (hit_dn & ~hit_up) | (both & (close[idx] < entry))
        label[up_win] = UP
        label[dn_win] = DOWN
        undecided &= ~(hit_up | hit_dn)

    with np.errstate(invalid="ignore", divide="ignore"):
        ret = np.where(ok, (close[end] - entry) / atr, np.nan)
    return BarrierLabels(label, ret.astype("float64"), end, np.asarray(atr, dtype="float64"))


def labels_from_ohlcv(ohlcv: pd.DataFrame, k: float = 1.5, horizon: int = 24,
                      atr_period: int = 51) -> BarrierLabels:
    """Ban dung tren du lieu that: ATR tinh nhan qua tu OHLC, phien = ngay giao dich."""
    h, l, c = (ohlcv[x].to_numpy("float64") for x in ("high", "low", "close"))
    atr = talib.ATR(h, l, c, timeperiod=atr_period)
    session = pd.factorize(ohlcv["date"])[0]
    return barrier_labels(ohlcv["open"].to_numpy("float64"), h, l, c, session, atr, k, horizon)
