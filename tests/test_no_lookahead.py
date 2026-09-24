"""Kiem tra tinh nhan qua - bai test quan trong nhat trong repo nay.

Mot dac trung "nhin trom" tuong lai khong lam pipeline bao loi. No chi lam backtest
dep len mot cach vo ly roi sup do khi chay that. Cach phat hien duy nhat dang tin
cay la: cat du lieu tai thoi diem t, tinh lai, va doi hoi gia tri tai t phai giong
het khi tinh tren toan bo chuoi. Neu khac, dac trung do da dung thong tin sau t.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from laplace.config import FeatureConfig
from laplace.dataset import window_ends
from laplace.loader import load_ohlcv
from laplace.pipeline import build_feature_frame, build_raw_features
from laplace.scaling import make_split

CUTS = (30_000, 60_000, 95_000)


@pytest.fixture(scope="module")
def cfg() -> FeatureConfig:
    return FeatureConfig()


@pytest.fixture(scope="module")
def raw(cfg) -> pd.DataFrame:
    return load_ohlcv(cfg)


@pytest.fixture(scope="module")
def full(cfg, raw) -> pd.DataFrame:
    return pd.concat(build_raw_features(raw, cfg).values(), axis=1)


@pytest.mark.parametrize("cut", CUTS)
def test_features_identical_when_future_removed(cfg, raw, full, cut):
    """Cat bo moi thu sau bar `cut` khong duoc lam doi gia tri tai cac bar truoc do."""
    truncated = pd.concat(build_raw_features(raw.iloc[:cut], cfg).values(), axis=1)
    tail = slice(cut - 200, cut)                       # 200 bar cuoi cua doan bi cat

    a = full[truncated.columns].iloc[tail].to_numpy(dtype="float64")
    b = truncated.iloc[tail].to_numpy(dtype="float64")

    both_nan = np.isnan(a) & np.isnan(b)
    diff = np.abs(a - b)
    diff[both_nan] = 0.0
    bad = ~(both_nan | (diff <= 1e-9))

    if bad.any():
        cols = np.asarray(truncated.columns)[bad.any(axis=0)]
        raise AssertionError(f"dac trung nhin trom tuong lai: {list(cols)[:20]}")


def test_split_is_ordered_and_embargoed(cfg, raw):
    """Ba tap phai theo thu tu thoi gian va co khe ho embargo giua chung."""
    fs = build_feature_frame(cfg, raw)
    idx = fs.features.index
    train, valid, test = fs.split.train, fs.split.valid, fs.split.test

    assert train.any() and valid.any() and test.any()
    assert not (train & valid).any() and not (valid & test).any()
    assert idx[train].max() < idx[valid].min() < idx[test].min()

    gap_valid = np.flatnonzero(valid)[0] - np.flatnonzero(train)[-1]
    gap_test = np.flatnonzero(test)[0] - np.flatnonzero(valid)[-1]
    assert gap_valid > cfg.embargo_bars
    assert gap_test > cfg.embargo_bars


def test_scaler_ignores_valid_and_test(cfg, raw):
    """Tham so scaler chi duoc phep phu thuoc vao tap train.

    Nhan doi gia tri dac trung trong vung valid/test; center va scale phai khong doi.
    """
    fs = build_feature_frame(cfg, raw)
    tampered = fs.features.copy()
    future = fs.split.valid | fs.split.test
    tampered.iloc[future] = tampered.iloc[future] * 1000.0

    from laplace.scaling import FeatureScaler

    refit = FeatureScaler(clip=cfg.clip_sigma, mode=cfg.scaler).fit(tampered, fs.split.train)
    np.testing.assert_allclose(refit.center, fs.scaler.center)
    np.testing.assert_allclose(refit.scale, fs.scaler.scale)


def test_windows_stay_inside_their_split(cfg, raw):
    """Cua so cua tap train khong duoc cham vao bar cua valid/test."""
    fs = build_feature_frame(cfg, raw)
    ends = window_ends(fs, cfg, fs.split.train)
    starts = ends - cfg.window + 1

    assert starts.min() >= 0
    assert fs.split.train[ends].all()
    assert fs.split.train[starts].all()


def test_window_does_not_cross_day_when_disabled(cfg, raw):
    """Voi cross_day=False, moi cua so phai nam gon trong mot phien."""
    intraday = FeatureConfig(window=24, cross_day=False)
    fs = build_feature_frame(intraday, raw)
    ends = window_ends(fs, intraday, np.ones(len(fs.features), dtype=bool))

    day = fs.ohlcv["date"].to_numpy()
    assert len(ends) > 0
    assert (day[ends] == day[ends - intraday.window + 1]).all()


def test_horizon_leaves_room_for_labels(cfg, raw):
    """Bar cuoi cua so phai con du bar tuong lai de gan nhan."""
    fs = build_feature_frame(cfg, raw)
    horizon = 12
    ends = window_ends(fs, cfg, np.ones(len(fs.features), dtype=bool), horizon=horizon)
    assert ends.max() + horizon < len(fs.features)
