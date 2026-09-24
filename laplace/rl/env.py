"""Moi truong giao dich vector hoa cho PPO (spec 004).

Mot loi goi `step()` xu ly ca N moi truong song song. Vong lap duy nhat trong huan
luyen la vong lap theo THOI GIAN, va no khong bo duoc: vi the tai bar t+1 phu thuoc
hanh dong tai bar t.

Thu tu trong mot buoc:

    bar t:  obs_t  = [cua so 64 bar ket o t, trang thai vi the tai t]
            a_t    = policy(obs_t)
            pos_t  = state.apply(a_t)                  <- co hieu luc tu cuoi bar t
            r_t    = pos_t * (c_{t+1} - c_t) / ATR_e  -  k*|dpos|
            t      = t + 1

Khong co gi nhin toi tuong lai: `pos_t` chi dung du lieu toi `t`, con `c_{t+1}` la ket
qua xay ra SAU quyet dinh - dung nhu ngoai doi.
"""

from __future__ import annotations

import numpy as np
import talib
import torch

from ..config import FeatureConfig
from ..pipeline import FeatureSet
from .state import PositionState

# Bon dac trung CO CHIEU, nhan voi dau vi the de head exit nhin thi truong "tu goc cua
# lenh dang cam" (spec 002 muc 2.5).
DIRECTIONAL = ("base__ret1", "base__ret12", "base__ret51", "bot__kespt_st_dist_atr")


class TradingEnv:
    """N moi truong song song chay tren cung mot cuon bang gia.

    Moi moi truong co con tro rieng va diem bat dau ngau nhien rieng. Do la nguon da
    dang duy nhat ta co, vi thi truong khong bao gio phan ung lai agent (spec 002).
    """

    def __init__(self, fs: FeatureSet, cfg: FeatureConfig, n_env: int = 128,
                 device: torch.device | str = "cpu", split: str = "train",
                 episode_len: int = 255, cost_per_turn: float = 0.0,
                 atr_period: int = 51, seed: int | None = None):
        self.cfg, self.n_env = cfg, n_env
        self.device = torch.device(device)
        self.episode_len = episode_len
        self.cost_per_turn = float(cost_per_turn)
        self.window = cfg.window

        # np.array(..., copy=True): pandas tra ve mang chi-doc, ma torch canh bao khi
        # boc tensor quanh no.
        t = lambda a, dt=torch.float32: torch.as_tensor(
            np.array(a, copy=True), dtype=dt, device=self.device)
        self.matrix = t(fs.matrix())
        o = fs.ohlcv
        self.close = t(o["close"].to_numpy())
        atr = talib.ATR(o["high"].to_numpy("float64"), o["low"].to_numpy("float64"),
                        o["close"].to_numpy("float64"), timeperiod=atr_period)
        # ATR chua on dinh o dau chuoi; day len 1 diem de khong bao gio chia cho 0.
        self.atr = t(np.nan_to_num(atr, nan=1.0)).clamp(min=1e-6)

        cols = list(fs.features.columns)
        missing = [c for c in DIRECTIONAL if c not in cols]
        if missing:
            raise ValueError(f"thieu dac trung co chieu: {missing}")
        self.dir_idx = t([cols.index(c) for c in DIRECTIONAL], torch.int64)

        self.starts = self._valid_starts(fs, split)
        self.state = PositionState(n_env, self.device, cfg.session_bars)
        self.cursor = torch.zeros(n_env, dtype=torch.int64, device=self.device)
        self.steps = torch.zeros(n_env, dtype=torch.int64, device=self.device)
        # Lai lo cua buoc vua roi, tinh bang DIEM. Cap nhat sau moi `step()`. Day la
        # thu dung de danh gia; `reward` chi de huan luyen (xem tu vung o CLAUDE.md).
        self.profit_points = torch.zeros(n_env, dtype=torch.float32, device=self.device)
        self._offsets = torch.arange(-self.window + 1, 1, device=self.device)
        self.generator = torch.Generator(device="cpu")
        if seed is not None:
            self.generator.manual_seed(seed)

    # ------------------------------------------------------------------ #
    def _valid_starts(self, fs: FeatureSet, split: str) -> torch.Tensor:
        """Cac bar dung lam diem bat dau ma CA episode nam gon trong mot tap.

        Ho hang cua bat bien #5: cua so lui ve qua khu va episode chay toi tuong lai
        deu phai nam trong cung mot tap, neu khong episode train se lan sang valid.
        """
        mask = np.asarray(getattr(fs.split, split))
        n = len(mask)
        ok = mask.copy()
        ok[: self.window - 1] = False              # khong du lich su
        ok[n - self.episode_len - 1:] = False      # khong du tuong lai

        idx = np.flatnonzero(ok)
        # Ca doan [start - window + 1, start + episode_len] phai nam trong cung mot tap.
        keep = idx[mask[idx - self.window + 1] & mask[idx + self.episode_len]]
        if not len(keep):
            raise ValueError(f"tap {split!r} qua ngan cho episode {self.episode_len} bar")
        return torch.as_tensor(keep, dtype=torch.int64, device=self.device)

    def _sample_starts(self, k: int) -> torch.Tensor:
        j = torch.randint(len(self.starts), (k,), generator=self.generator)
        return self.starts[j.to(self.device)]

    # ------------------------------------------------------------------ #
    def price(self) -> torch.Tensor:
        return self.close[self.cursor]

    def observation(self) -> tuple[torch.Tensor, torch.Tensor]:
        """Tra ve (cua so (N, window, F), vector trang thai (N, 10))."""
        win = self.matrix[self.cursor[:, None] + self._offsets[None, :]]
        directional = win[:, -1][:, self.dir_idx]
        return win, self.state.state_vector(self.price(), directional)

    def reset(self, mask: torch.Tensor | None = None):
        """Dat lai cac moi truong duoc chon vao mot diem bat dau ngau nhien moi."""
        if mask is None:
            mask = torch.ones(self.n_env, dtype=torch.bool, device=self.device)
        k = int(mask.sum())
        if k:
            self.cursor[mask] = self._sample_starts(k)
            self.steps = torch.where(mask, torch.zeros_like(self.steps), self.steps)
            self.state.reset(mask)
        return self.observation()

    # ------------------------------------------------------------------ #
    def reward_from(self, position: float, d_close: float, atr_entry: float,
                    d_position: float) -> float:
        """REWARD cho mot truong hop don le - viet ro de test doc duoc.

            reward = pos * dc / ATR_e  -  k * |dpos|      [boi so ATR]

        Chia cho ATR luc VAO LENH: tong reward cua mot lenh thanh (thoat - vao)/ATR_e,
        dung khai niem boi so R. Neu dung ATR hien tai thi tong la sum(dc_t / ATR_t),
        khong phai mot dai luong co y nghia.

        Day KHONG phai profit. Profit tinh bang diem: `profit_from()`.
        """
        return position * d_close / atr_entry - self.cost_per_turn * abs(d_position)

    def profit_from(self, position: float, d_close: float) -> float:
        """PROFIT cho mot truong hop don le, tinh bang DIEM chi so.

            profit = pos * dc                             [diem]

        Khong chia ATR, khong tru chi phi giao dich o day - chi phi la khoan rieng khi
        tinh hieu qua. Day la thu dung de bao cao thanh tich.
        """
        return position * d_close

    def step(self, entry_action: torch.Tensor, exit_action: torch.Tensor):
        """Ap hanh dong. Tra ve ((cua so, vector trang thai), thuong, co tam dung)."""
        price = self.price()
        prev_position = self.state.position.to(price.dtype)

        new_position = self.state.apply(entry_action, exit_action, price, self.atr[self.cursor])
        pos = new_position.to(price.dtype)

        nxt = torch.clamp(self.cursor + 1, max=len(self.close) - 1)
        d_close = self.close[nxt] - price
        live = new_position != 0

        # PROFIT: lai lo that, tinh bang DIEM chi so. Day la thu de danh gia.
        self.profit_points = torch.where(live, pos * d_close, torch.zeros_like(d_close))

        # REWARD: tin hieu huan luyen, tinh bang BOI SO ATR. Khong phai profit va khong
        # ty le voi profit - chia cho ATR lam moi che do bien dong dong gop ngang nhau
        # khi hoc. Do tren bot KESPT: ty le R tren moi diem chay tu 0,26 den 1,34 tuy
        # nam. Xem muc tu vung trong CLAUDE.md.
        # `entry_atr` da duoc `apply` cap nhat cho lenh vua mo, nen mau so luon la ATR
        # cua chinh lenh dang cam.
        r_atr = pos * d_close / self.state.entry_atr
        cost = self.cost_per_turn * (pos - prev_position).abs()
        reward = torch.where(live, r_atr, torch.zeros_like(r_atr)) - cost

        self.cursor = nxt
        self.steps = self.steps + 1
        self.state.advance(self.price())

        truncated = self.steps >= self.episode_len
        return self.observation(), reward, truncated
