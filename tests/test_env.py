"""Canh spec 004 - ham reward va moi truong vector hoa.

Bai quan trong nhat la `test_reward_telescopes_to_realised_pnl` (bat bien #17). Neu
tong thuong tung bar khong bang lai lo thuc hien cua lenh, agent dang duoc thuong cho
mot thu khong phai tien - va moi ket qua backtest ve sau deu vo nghia ma khong co gi bao.
"""

from __future__ import annotations

import numpy as np
import pytest
import torch

from laplace.config import FeatureConfig
from laplace.rl.env import TradingEnv
from laplace.rl.state import ENTRY_LONG, ENTRY_SHORT, ENTRY_SKIP, EXIT_EXIT, EXIT_HOLD

N_ENV = 16


@pytest.fixture(scope="module")
def cfg() -> FeatureConfig:
    return FeatureConfig()


@pytest.fixture(scope="module")
def fs(cfg):
    from laplace.pipeline import build_feature_frame

    return build_feature_frame(cfg)


@pytest.fixture
def env(fs, cfg):
    return TradingEnv(fs, cfg, n_env=N_ENV, device=torch.device("cpu"), seed=0)


def _act(env, entry: int, exit_: int):
    e = torch.full((env.n_env,), entry, dtype=torch.int64, device=env.device)
    x = torch.full((env.n_env,), exit_, dtype=torch.int64, device=env.device)
    return env.step(e, x)


# --------------------------------------------------------------------------- #
# Reward
# --------------------------------------------------------------------------- #
def test_reward_telescopes_to_realised_pnl(env):
    """Bat bien 17: cong don thuong tung bar = lai lo thuc hien cua lenh, tinh bang ATR.

    Vao LONG, giu 10 bar, thoat. Tong thuong phai bang (gia thoat - gia vao)/ATR_e.
    """
    env.reset()
    entry_price = env.price().clone()

    total = torch.zeros(env.n_env, device=env.device)
    _, r, _ = _act(env, ENTRY_LONG, EXIT_HOLD)      # vao LONG o bar nay
    total += r
    atr_e = env.state.entry_atr.clone()

    for _ in range(9):
        _, r, _ = _act(env, ENTRY_SKIP, EXIT_HOLD)
        total += r

    exit_price = env.price().clone()
    _, r, _ = _act(env, ENTRY_SKIP, EXIT_EXIT)      # thoat: pos ve 0 nen r = 0
    total += r

    expected = (exit_price - entry_price) / atr_e
    torch.testing.assert_close(total, expected, rtol=1e-4, atol=1e-4)


def test_reward_is_zero_while_flat(env):
    """Quen mask luc FLAT thi agent duoc thuong cho vi the no khong he co."""
    env.reset()
    for _ in range(20):
        _, r, _ = _act(env, ENTRY_SKIP, EXIT_HOLD)
        assert torch.all(r == 0), "FLAT ma van co thuong"


def test_reward_uses_entry_atr_not_current_atr(env):
    """Mau so phai dong bang tai bar vao lenh.

    Neu dung ATR hien tai, tong thuong khong con la boi so R va cung khong con khop voi
    bien trang thai `pos_pnl_atr` (spec 002 dung ATR luc vao lenh).
    """
    env.reset()
    _act(env, ENTRY_LONG, EXIT_HOLD)
    atr_e = env.state.entry_atr.clone()

    for _ in range(30):
        before = env.price().clone()
        _, r, _ = _act(env, ENTRY_SKIP, EXIT_HOLD)
        after = env.price()
        torch.testing.assert_close(r, (after - before) / atr_e, rtol=1e-4, atol=1e-5)


def test_reward_is_scale_free_across_volatility_regimes(env):
    """Cung mot lenh 2R o hai che do bien dong phai cho cung mot thuong."""
    r_lo = env.reward_from(position=1.0, d_close=6.0, atr_entry=3.0, d_position=0.0)
    r_hi = env.reward_from(position=1.0, d_close=30.0, atr_entry=15.0, d_position=0.0)
    assert r_lo == pytest.approx(2.0) and r_hi == pytest.approx(2.0)


def test_reversal_is_charged_two_turns(fs, cfg):
    """Dao chieu sinh HAI luot giao dich, phai bi tru 2k chu khong phai k."""
    env = TradingEnv(fs, cfg, n_env=N_ENV, device=torch.device("cpu"), seed=0,
                     cost_per_turn=0.25)
    one = env.reward_from(position=1.0, d_close=0.0, atr_entry=1.0, d_position=1.0)
    two = env.reward_from(position=-1.0, d_close=0.0, atr_entry=1.0, d_position=2.0)
    assert one == pytest.approx(-0.25)
    assert two == pytest.approx(-0.50), "dao chieu phai bi tru gap doi"


def test_cost_defaults_to_zero(env):
    """Giai doan phat trien chay voi chi phi 0, nhung tham so phai ton tai."""
    assert env.cost_per_turn == 0.0


# --------------------------------------------------------------------------- #
# Episode
# --------------------------------------------------------------------------- #
def test_episode_truncates_at_configured_length(env):
    """Sau dung `episode_len` buoc thi bao tam dung, va KHONG ep dong lenh."""
    env.reset()
    _act(env, ENTRY_LONG, EXIT_HOLD)                       # buoc 1
    for step in range(2, env.episode_len):                 # toi buoc 254
        _, _, trunc = _act(env, ENTRY_SKIP, EXIT_HOLD)
        assert not trunc.any(), f"tam dung qua som o buoc {step}"
    _, _, trunc = _act(env, ENTRY_SKIP, EXIT_HOLD)         # buoc 255
    assert trunc.all(), "phai tam dung o dung episode_len"


def test_episode_never_leaves_its_split(fs, cfg):
    """Ho hang cua bat bien #5: episode train khong duoc lan sang valid hay test."""
    env = TradingEnv(fs, cfg, n_env=64, device=torch.device("cpu"), seed=7)
    mask = torch.as_tensor(fs.split.train)
    for _ in range(6):
        env.reset()
        start = env.cursor.clone()
        assert bool(mask[start - cfg.window + 1].all()), "cua so lui ra ngoai tap"
        for _ in range(env.episode_len):
            _act(env, ENTRY_SKIP, EXIT_HOLD)
            assert bool(mask[env.cursor].all()), "con tro di ra ngoai tap"


# --------------------------------------------------------------------------- #
# Quan sat va toc do
# --------------------------------------------------------------------------- #
def test_observation_matches_sequence_dataset(env, fs, cfg):
    """Cua so cua moi truong phai trung khit cua so cua SequenceDataset.

    Neu lech, moi truong dang tu bia ra mot duong du lieu thu hai va moi thu da kiem
    chung tren `dataset.py` khong con bao dam gi.
    """
    from laplace.dataset import SequenceDataset

    obs, _ = env.reset()
    matrix = fs.matrix()
    ds = SequenceDataset(matrix, env.cursor.cpu().numpy(), cfg.window)
    torch.testing.assert_close(obs.cpu(), torch.from_numpy(ds.to_array()))


def test_step_is_vectorised_over_environments(fs, cfg):
    """Mot loi goi xu ly ca lo. Vong lap Python tren chieu moi truong lam sut hang chuc lan.

    Do o 128 moi truong tren CPU cho on dinh; nguong dat that thap vi day chi la canh
    hoi quy chu khong phai bai do hieu nang.
    """
    import time

    env = TradingEnv(fs, cfg, n_env=128, device=torch.device("cpu"), seed=0)
    env.reset()
    for _ in range(5):
        _act(env, ENTRY_SKIP, EXIT_HOLD)
    t0 = time.perf_counter()
    for _ in range(50):
        _act(env, ENTRY_SKIP, EXIT_HOLD)
    bars = 128 * 50 / (time.perf_counter() - t0)
    assert bars > 20_000, f"chi {bars:,.0f} bar/s - co vong lap tren chieu moi truong?"


def test_reset_gives_each_environment_a_different_start(fs, cfg):
    env = TradingEnv(fs, cfg, n_env=64, device=torch.device("cpu"), seed=3)
    env.reset()
    assert len(torch.unique(env.cursor)) > 32, "diem bat dau khong du da dang"


def test_profit_and_reward_are_different_quantities(env):
    """Tu vung: `profit` tinh bang DIEM, `reward` tinh bang boi so ATR (CLAUDE.md).

    Hai dai luong nay khong ty le voi nhau vi reward chia cho ATR luc vao lenh. Do tren
    bot KESPT: ty le R tren moi diem chay tu 0,26 (2017) den 1,34 (2019), va xep hang
    cac nam theo hai thuoc do cho ra thu tu khac nhau. Lan lon hai cai la cach nhanh
    nhat de bao cao mot con so vo nghia.
    """
    env.reset()
    before = env.price().clone()
    _, reward, _ = _act(env, ENTRY_LONG, EXIT_HOLD)
    after = env.price()
    atr_e = env.state.entry_atr

    # profit = pos * dc, tinh bang diem
    torch.testing.assert_close(env.profit_points, after - before, rtol=1e-4, atol=1e-4)
    # reward = profit / ATR_e, tinh bang boi so R
    torch.testing.assert_close(reward, env.profit_points / atr_e, rtol=1e-4, atol=1e-5)
    # ATR khac 1 nen hai dai luong khong the bang nhau
    assert (atr_e > 1.0).any(), "can ATR != 1 de phep kiem tra nay co y nghia"
    assert not torch.allclose(reward, env.profit_points)


def test_profit_is_reported_in_points_not_atr(env):
    """`profit_from` khong duoc chia ATR - do la viec cua `reward_from`."""
    assert env.profit_from(position=1.0, d_close=6.0) == pytest.approx(6.0)
    assert env.reward_from(position=1.0, d_close=6.0, atr_entry=3.0,
                           d_position=0.0) == pytest.approx(2.0)
