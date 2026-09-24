"""Canh spec 006 - lop tinh dung.

Hai nua cua phuong an A phai dung CUNG LUC:
  - cot `adaptive` (dong lenh) phai QUEN mot cu dich muc keo dai - do la loi do;
  - cot muc cua lop `variance` phai NHO che do bien dong - do la thong tin that.
Mot bai chi kiem nua dau thi phuong an B (rolling z cho moi thu) cung qua duoc.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from laplace.config import FeatureConfig
from laplace.stationarity import classify, pit, rolling_zscore, stationarize


@pytest.fixture(scope="module")
def cfg() -> FeatureConfig:
    return FeatureConfig()


def _series(columns: dict) -> pd.DataFrame:
    n = len(next(iter(columns.values())))
    idx = pd.date_range("2020-01-01", periods=n, freq="5min")
    return pd.DataFrame(columns, index=idx)


def test_adaptive_column_forgets_a_level_shift(cfg):
    """Mo phong OFI 2023: muc nhay +0,2 va o luon do."""
    rng = np.random.default_rng(0)
    n, jump, w = 3000, 1500, cfg.rolling_window
    x = rng.normal(0.0, 0.1, n)
    x[jump:] += 0.2
    out = stationarize(_series({"flow__ofi_ma12": x}), cfg)["flow__ofi_ma12"].to_numpy()

    just_after = np.median(out[jump:jump + 20])
    long_after = np.median(out[jump + w:])
    assert just_after > 0.5, f"cu nhay phai hien ro ngay sau khi xay ra: {just_after:+.3f}"
    assert abs(long_after) < 0.1, f"sau W bar muc moi phai thanh binh thuong: {long_after:+.3f}"


def test_variance_level_keeps_the_regime_and_z_forgets_it(cfg):
    """Bien dong nhan doi: cot muc phai giu chenh log 2, cot _z phai ve 0."""
    rng = np.random.default_rng(1)
    n, jump, w = 4000, 2000, cfg.rolling_window
    x = np.abs(rng.normal(0.004, 0.0004, n))
    x[jump:] *= 2.0
    out = stationarize(_series({"volatility__ATR12": x}), cfg)

    level = out["volatility__ATR12"].to_numpy()
    gap = np.median(level[jump + w:]) - np.median(level[:jump])
    assert gap == pytest.approx(np.log(2.0), abs=0.05), \
        f"cot muc phai nho che do: chenh {gap:.3f}, ky vong log 2 = {np.log(2):.3f}"

    z = out["volatility__ATR12_z"].to_numpy()
    assert abs(np.median(z[jump + w:])) < 0.1, "cot _z phai coi che do moi la binh thuong"


def test_rolling_zscore_uses_only_the_past(cfg):
    """Sua x tai t va sau do: z truoc t khong doi. Sua x_t: mu_t khong doi."""
    rng = np.random.default_rng(2)
    df = _series({"a": rng.normal(size=800)})
    base = rolling_zscore(df, 100)

    t = 500
    changed = df.copy()
    changed.iloc[t:] += 50.0
    after = rolling_zscore(changed, 100)
    pd.testing.assert_frame_equal(base.iloc[:t], after.iloc[:t])

    # Neu mu_t dung ca x_t thi z_t se bi keo ve 0 khi x_t cuc lon.
    spike = df.copy()
    spike.iloc[t] = 1e6
    assert rolling_zscore(spike, 100).iloc[t, 0] > 1e4, "thong ke cuon dang dung ca bar hien tai"


def test_constant_past_gives_a_defined_zscore_not_nan():
    """Qua khu hang so: bang no -> 0, lech khoi no -> +-inf. Khong duoc NaN.

    Da xay ra that: `flow__participation` hang so toi 08/2018, z thanh NaN va burn-in
    dai them 7.843 bar - mat 8 thang du lieu train ma khong co loi nao bao.
    """
    x = np.r_[np.ones(300), 1.0, 1.5, 0.5]
    z = rolling_zscore(_series({"a": x}), 100)["a"].to_numpy()
    assert np.isnan(z[0]), "bar dau chua co qua khu - van phai NaN"
    assert z[299] == 0.0 and z[300] == 0.0
    assert z[301] == np.inf
    # Bar 302: qua khu da chua 1,5 nen khong con hang so - z huu han, am.
    assert np.isfinite(z[302]) and z[302] < -5


def test_pit_is_bounded_and_monotone(cfg):
    z = np.linspace(-50, 50, 1001)
    u = pit(z, cfg.pit_dof)
    assert np.all((u > -1) & (u < 1))
    assert pit(np.array([np.inf, -np.inf]), cfg.pit_dof).tolist() == [1.0, -1.0]
    assert np.all(np.diff(u) >= 0)
    assert pit(np.array([0.0]), cfg.pit_dof)[0] == pytest.approx(0.0, abs=1e-12)
    # Duoi day: mot cu 6 sigma khong con chiem tron thang do.
    assert pit(np.array([6.0]), cfg.pit_dof)[0] < 0.999
    assert np.isnan(pit(np.array([np.nan]), cfg.pit_dof)[0])


@pytest.mark.parametrize("col, expected", [
    ("flow__ofi_ma255", "adaptive"),          # adaptive dung truoc regime
    ("flow__cum_delta_day", "adaptive"),
    ("flow__active_rel255", "regime"),        # khong phu thuoc cach phan loai mua/ban
    ("flow__active_rel12", "stationary"),
    ("volatility__ATR12", "variance"),
    ("volatility__TRANGE", "variance"),
    ("base__rv51", "variance"),
    ("base__park255", "variance"),
    ("statistic__STDDEV24", "variance"),
    ("momentum__PLUS_DM6", "variance"),
    ("bot__kespt_st_up", "variance"),
    ("bot__kespt_atr28", "variance"),         # lo ra khi ATR24 thanh log, het trung lap
    ("base__rv255_z", "stationary"),          # _z khong duoc tron vao regime
    ("overlap__SMA255", "regime"),
    ("volume__ADOSC_51_102", "regime"),
    ("bot__kespt_ema300", "regime"),
    ("momentum__RSI51", "stationary"),
    ("momentum__PLUS_DI24", "stationary"),
    ("base__ret1_z", "stationary"),
])
def test_classes_follow_the_rules(cfg, col, expected):
    assert classify(col, cfg) == expected
