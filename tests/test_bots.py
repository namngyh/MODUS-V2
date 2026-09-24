"""Kiem tra ban dich AFL -> Python va chuoi tin hieu cua hai bot."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from laplace.afl import cross, exrem, flip, position_from_signals, ref, stoch_k
from laplace.bots import build_bot_signals, run_kespt, run_roofing
from laplace.config import FeatureConfig
from laplace.loader import load_ohlcv
from laplace.pipeline import build_feature_frame, run_bots


@pytest.fixture(scope="module")
def cfg() -> FeatureConfig:
    return FeatureConfig()


@pytest.fixture(scope="module")
def raw(cfg) -> pd.DataFrame:
    return load_ohlcv(cfg)


@pytest.fixture(scope="module")
def runs(raw):
    return run_bots(raw)


# --------------------------------------------------------------------------- #
# Ham co ban AFL - kiem bang vi du tinh tay
# --------------------------------------------------------------------------- #
def test_cross_fires_only_on_the_crossing_bar():
    a = np.array([1.0, 1.0, 3.0, 4.0, 1.0, 5.0])
    b = np.array([2.0, 2.0, 2.0, 2.0, 2.0, 2.0])
    #             duoi  duoi  CAT   tren  duoi  CAT
    np.testing.assert_array_equal(cross(a, b), [False, False, True, False, False, True])


def test_cross_needs_strict_break_not_touch():
    """Cham dung bang khong phai cat: a == b khong kich hoat tin hieu."""
    a = np.array([1.0, 2.0, 2.0])
    b = np.array([2.0, 2.0, 2.0])
    assert not cross(a, b).any()


def test_flip_holds_state_and_on_wins_ties():
    on = np.array([1, 0, 0, 1, 0], dtype=bool)
    off = np.array([0, 0, 1, 1, 0], dtype=bool)
    #  bar0 bat -> 1 ; bar2 tat -> 0 ; bar3 ca hai -> `on` thang -> 1
    np.testing.assert_array_equal(flip(on, off), [True, True, False, True, True])


def test_exrem_keeps_only_first_signal_until_reset():
    sig = np.array([1, 1, 1, 0, 1, 1], dtype=bool)
    reset = np.array([0, 0, 0, 1, 0, 0], dtype=bool)
    np.testing.assert_array_equal(exrem(sig, reset), [True, False, False, False, True, False])


def test_ref_rejects_looking_forward():
    with pytest.raises(ValueError):
        ref(np.arange(5.0), 1)
    np.testing.assert_array_equal(ref(np.arange(5.0), -2)[2:], [0.0, 1.0, 2.0])


def test_stoch_k_spans_zero_to_hundred():
    n = 200
    rng = np.random.default_rng(0)
    close = 100 + np.cumsum(rng.normal(0, 1, n))
    high, low = close + 1, close - 1
    k = stoch_k(high, low, close, 22, 43)
    valid = k[~np.isnan(k)]
    assert len(valid) > 100
    assert valid.min() >= 0.0 and valid.max() <= 100.0


def test_stoch_k_flat_range_does_not_divide_by_zero():
    """Bar phang (H == L trong ca cua so) tung lam vo cong thuc %K."""
    close = np.full(100, 50.0)
    k = stoch_k(close, close, close, 22, 43)
    finite = k[~np.isnan(k)]
    assert len(finite) > 0
    assert np.isfinite(finite).all()


def test_position_state_machine_handles_reversal():
    #        bar:   0      1      2      3
    buy = np.array([1, 0, 0, 0], dtype=bool)
    sell = np.array([0, 0, 1, 0], dtype=bool)
    short = np.array([0, 0, 1, 0], dtype=bool)   # dao chieu ngay trong bar 2
    cover = np.array([0, 0, 0, 1], dtype=bool)
    np.testing.assert_array_equal(
        position_from_signals(buy, sell, short, cover), [1, 1, -1, 0]
    )


# --------------------------------------------------------------------------- #
# Tin hieu bot
# --------------------------------------------------------------------------- #
def test_signals_are_ternary(raw, runs):
    sig = build_bot_signals(raw, runs)
    for bot in ("kespt", "roofing", "both"):
        assert set(np.unique(sig[f"{bot}_pos"])) <= {-1, 0, 1}


def test_position_changes_only_on_event_bars(raw, runs):
    """Vi the khong duoc doi o bar khong co tin hieu vao/ra nao."""
    sig = build_bot_signals(raw, runs)
    for bot in ("kespt", "roofing"):
        pos = sig[f"{bot}_pos"].to_numpy().astype("int8")
        changed = np.append(False, pos[1:] != pos[:-1])
        events = (sig[f"{bot}_buy"] | sig[f"{bot}_sell"]
                  | sig[f"{bot}_short"] | sig[f"{bot}_cover"]).to_numpy().astype(bool)
        assert not (changed & ~events).any()


def test_both_pos_is_the_intersection(raw, runs):
    sig = build_bot_signals(raw, runs)
    agree = sig["kespt_pos"] == sig["roofing_pos"]
    np.testing.assert_array_equal(sig.loc[agree, "both_pos"], sig.loc[agree, "kespt_pos"])
    assert (sig.loc[~agree, "both_pos"] == 0).all()


def test_both_bots_actually_trade(raw, runs):
    """Loi dich AFL hay bieu hien thanh bot khong bao gio vao lenh, hoac vao lien tuc."""
    sig = build_bot_signals(raw, runs)
    for bot in ("kespt", "roofing"):
        entries = int(sig[f"{bot}_buy"].sum() + sig[f"{bot}_short"].sum())
        in_market = float((sig[f"{bot}_pos"] != 0).mean())
        assert 300 < entries < 20_000
        assert 0.02 < in_market < 0.95


@pytest.mark.parametrize("cut", (40_000, 80_000))
def test_signals_do_not_use_future_bars(cfg, raw, runs, cut):
    """Cat du lieu tai `cut` roi chay lai: tin hieu truoc do phai giu nguyen.

    SuperTrend va Roofing Filter deu de quy, nen day la bai kiem tra co y nghia:
    mot loi chi so lech mot bar trong vong lap se hien ra ngay o day.
    """
    full = build_bot_signals(raw, runs)
    part = build_bot_signals(raw.iloc[:cut], run_bots(raw.iloc[:cut]))
    tail = slice(cut - 500, cut)
    pd.testing.assert_frame_equal(full.iloc[tail], part.iloc[tail])


def test_signals_align_with_features_after_burn_in(cfg, raw):
    fs = build_feature_frame(cfg, raw)
    assert fs.signals is not None
    assert len(fs.signals) == len(fs.features)
    pd.testing.assert_index_equal(fs.signals.index, fs.features.index)


def test_signals_stay_out_of_the_feature_matrix(cfg, raw):
    """Tin hieu la thu de doi chieu, khong phai dau vao - de no lot vao X thi mo
    hinh chi hoc cach sao chep bot."""
    fs = build_feature_frame(cfg, raw)
    assert not set(fs.signals.columns) & set(fs.columns)
    assert not any(c.endswith("_pos") for c in fs.columns)


def test_bot_feature_group_is_present(cfg, raw):
    fs = build_feature_frame(cfg, raw)
    assert len(fs.groups["bot"]) > 10
    # Cac dai luong loi cua ca hai bot phai song sot qua buoc tia cot.
    for name in ("bot__kespt_st_dist_atr", "bot__kespt_storsi",
                 "bot__roof_filt", "bot__roof_momz"):
        assert name in fs.columns


def test_supertrend_line_sits_on_the_right_side_of_price(raw):
    """Khi trend = 1 duong ST la san (duoi gia), khi trend = -1 la tran (tren gia).

    Day la bat bien cua SuperTrend; dao thu tu cap nhat trong vong lap se pha vo no.
    """
    run = run_kespt(raw)
    v = run.values
    close = raw["close"].to_numpy()
    warm = 100                                       # bo qua doan ATR chua on dinh
    up_trend = (v["st_trend"] == 1) & np.isfinite(v["st_line"])
    up_trend[:warm] = False
    dn_trend = (v["st_trend"] == -1) & np.isfinite(v["st_line"])
    dn_trend[:warm] = False

    assert (v["st_line"][up_trend] <= close[up_trend]).mean() > 0.99
    assert (v["st_line"][dn_trend] >= close[dn_trend]).mean() > 0.99


def test_roofing_filter_is_zero_centred(raw):
    """High-pass phai loai bo hoan toan thanh phan xu the: gia di tu 600 len 1900
    ma Filt van dao dong quanh 0."""
    run = run_roofing(raw)
    filt = run.values["filt"][1000:]
    assert abs(filt.mean()) < 0.05 * filt.std()
