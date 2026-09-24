"""Canh spec 005 - vong PPO va danh gia.

Bai quan trong nhat la `test_boundary_bootstraps_instead_of_zeroing_future` (bat bien
#18). Thi truong khong bao gio "ket thuc" - moi ranh gioi episode deu la TAM DUNG. Gan
tuong lai bang 0 tai do se keo lech ham gia tri o moi trang thai gan ranh gioi, ma diem
cat lai ngau nhien nen sai lech trai deu len toan bo du lieu. Khong co trieu chung nao
ngoai viec mo hinh hoc kem hon muc dang le.
"""

from __future__ import annotations

import numpy as np
import pytest
import torch

from laplace.config import FeatureConfig
from laplace.rl.env import TradingEnv
from laplace.rl.policy import Policy
from laplace.rl.ppo import PPOConfig, PPOTrainer, compute_gae
from laplace.rl.state import N_STATE


@pytest.fixture(scope="module")
def cfg() -> FeatureConfig:
    return FeatureConfig()


@pytest.fixture(scope="module")
def fs(cfg):
    from laplace.pipeline import build_feature_frame

    return build_feature_frame(cfg)


@pytest.fixture
def trainer(fs, cfg):
    env = TradingEnv(fs, cfg, n_env=8, device=torch.device("cpu"), seed=0)
    policy = Policy(n_features=fs.matrix().shape[1], window=cfg.window)
    return PPOTrainer(policy, env, PPOConfig(n_steps=16, n_epochs=1, minibatch=32),
                      device=torch.device("cpu"))


# --------------------------------------------------------------------------- #
# GAE
# --------------------------------------------------------------------------- #
def test_gae_matches_hand_computation():
    """Bon buoc, khong ranh gioi nao. Tinh tay tung so."""
    g, lam = 0.9, 0.8
    rewards = torch.tensor([[1.0], [2.0], [3.0], [4.0]])
    values = torch.tensor([[0.5], [1.0], [1.5], [2.0]])
    next_values = torch.tensor([[1.0], [1.5], [2.0], [2.5]])
    cut = torch.zeros(4, 1, dtype=torch.bool)

    adv, ret = compute_gae(rewards, values, next_values, cut, gamma=g, lam=lam)

    v_next = [1.0, 1.5, 2.0, 2.5]
    expect, carry = [0.0] * 4, 0.0
    for t in reversed(range(4)):
        delta = rewards[t, 0] + g * v_next[t] - values[t, 0]
        carry = delta + g * lam * carry
        expect[t] = carry
    torch.testing.assert_close(adv[:, 0], torch.tensor(expect))
    torch.testing.assert_close(ret[:, 0], adv[:, 0] + values[:, 0])


def test_boundary_bootstraps_instead_of_zeroing_future():
    """Bat bien 18: tai ranh gioi van dung V(s_{t+1}), khong gan tuong lai = 0.

    Dung mot bar co ranh gioi va so advantage voi phien ban gan V = 0. Hai ket qua PHAI
    khac nhau; neu giong nhau thi code dang coi tam dung nhu ket thuc.
    """
    g, lam = 0.99, 0.95
    rewards = torch.tensor([[1.0], [1.0], [1.0]])
    values = torch.tensor([[5.0], [5.0], [5.0]])
    next_values = torch.tensor([[5.0], [5.0], [7.0]])
    cut = torch.tensor([[False], [True], [False]])      # ranh gioi o buoc 1

    adv, _ = compute_gae(rewards, values, next_values, cut, gamma=g, lam=lam)

    # Buoc 1 la ranh gioi: delta van phai gom g*V(s_2) = 0,99*5 = 4,95
    delta1 = 1.0 + g * 5.0 - 5.0
    assert adv[1, 0].item() == pytest.approx(delta1, abs=1e-5)
    assert adv[1, 0].item() > 0.9, "gan tuong lai = 0 se cho advantage am"


def test_gae_recursion_is_cut_at_boundaries():
    """Advantage cua episode sau khong duoc lan nguoc ve episode truoc."""
    g, lam = 0.99, 0.95
    rewards = torch.tensor([[0.0], [0.0], [100.0]])
    values = torch.zeros(3, 1)
    next_values = torch.zeros(3, 1)

    no_cut, _ = compute_gae(rewards, values, next_values,
                            torch.zeros(3, 1, dtype=torch.bool), gamma=g, lam=lam)
    with_cut, _ = compute_gae(rewards, values, next_values,
                              torch.tensor([[False], [True], [False]]), gamma=g, lam=lam)

    assert no_cut[0, 0] > 80, "khong cat thi phan thuong lon phai lan nguoc ve"
    assert with_cut[0, 0].item() == pytest.approx(0.0, abs=1e-6), \
        "co cat thi khong duoc lan qua ranh gioi"


# --------------------------------------------------------------------------- #
# Cap nhat policy
# --------------------------------------------------------------------------- #
def test_ratio_uses_summed_log_prob_for_compound_actions(trainer):
    """Bar dao chieu dung ca hai head, nen ratio phai dung TONG hai log-prob.

    Chi lay mot so hang thi ty le importance sai ma khong co gi bao (spec 002).
    """
    from laplace.rl.state import ENTRY_SHORT, EXIT_EXIT

    n = 4
    win = torch.randn(n, trainer.env.window, trainer.policy.n_features)
    sv = torch.randn(n, N_STATE)
    pos = torch.ones(n, dtype=torch.int8)                 # dang LONG
    entry_a = torch.full((n,), ENTRY_SHORT, dtype=torch.int64)
    exit_a = torch.full((n,), EXIT_EXIT, dtype=torch.int64)

    logp = trainer.log_prob_of(win, sv, pos, entry_a, exit_a)
    e_lp, x_lp = trainer.policy.action_log_probs(win, sv, pos, entry_a, exit_a)
    torch.testing.assert_close(logp, e_lp + x_lp)


def test_clipping_limits_the_policy_update(trainer):
    """Advantage lon den may cung khong duoc keo ratio ra ngoai [1-eps, 1+eps]."""
    eps = trainer.cfg.clip_eps
    ratio = torch.tensor([0.1, 0.5, 1.0, 2.0, 10.0])
    adv = torch.full_like(ratio, 1000.0)
    loss = trainer.policy_loss(ratio, adv)
    hand = -torch.min(ratio * adv, ratio.clamp(1 - eps, 1 + eps) * adv).mean()
    torch.testing.assert_close(loss, hand)
    assert loss.item() >= -1000.0 * (1 + eps) - 1e-3


def test_update_moves_probability_toward_high_advantage_actions(trainer):
    """Sau cap nhat, hanh dong co advantage duong phai tro nen KHA DI hon.

    Do la dinh nghia cua PPO, va la thu duy nhat dang do o day. Hai thuoc do tu nhien
    hon deu sai:

    - TONG LOSS khong don dieu giam: muc tieu chinh sach bi CAT nen chung lai khi policy
      di qua bien, con entropy thi tut khi policy sac lai ma loss lai TRU entropy.
    - VALUE LOSS cung khong: head gia tri dung chung encoder voi head chinh sach, nen
      gradient cua policy loss keo encoder di va lam value du doan lech theo.
    """
    torch.manual_seed(0)
    batch = trainer.collect()
    flat = lambda x: x.reshape(-1, *x.shape[2:])
    win, sv = flat(batch["win"]), flat(batch["sv"])
    pos, ea, xa = flat(batch["pos"]), flat(batch["entry"]), flat(batch["exit"])
    adv = flat(batch["advantage"])

    with torch.no_grad():
        before = trainer.log_prob_of(win, sv, pos, ea, xa)
    for _ in range(5):
        trainer.update(batch)
    with torch.no_grad():
        after = trainer.log_prob_of(win, sv, pos, ea, xa)

    delta = after - before
    corr = torch.corrcoef(torch.stack([delta, adv]))[0, 1]
    assert corr > 0.1, f"xac suat khong dich theo advantage: corr = {corr:+.3f}"


# --------------------------------------------------------------------------- #
# Danh gia
# --------------------------------------------------------------------------- #
def test_evaluation_reports_profit_in_points(fs, cfg):
    """Bao cao hieu qua bang DIEM. `reward` chi de chan doan (tu vung o CLAUDE.md)."""
    from laplace.rl.evaluate import evaluate

    policy = Policy(n_features=fs.matrix().shape[1], window=cfg.window)
    out = evaluate(policy, fs, cfg, split="valid", device=torch.device("cpu"), seed=0)

    assert "profit_points" in out and np.isfinite(out["profit_points"])
    assert "max_drawdown_points" in out
    assert "n_trades" in out and "time_in_market" in out
    assert "reward_mean" in out, "van giu reward de chan doan, chi khong bao cao no"


def test_evaluation_covers_the_split_in_time_order(fs, cfg):
    """Danh gia chay het tap theo dung thu tu thoi gian, khong cat ngau nhien."""
    from laplace.rl.evaluate import evaluate

    policy = Policy(n_features=fs.matrix().shape[1], window=cfg.window)
    out = evaluate(policy, fs, cfg, split="valid", device=torch.device("cpu"), seed=0)
    n_valid = int(fs.split.valid.sum())
    assert out["n_bars"] > 0.9 * n_valid, \
        f"chi chay {out['n_bars']} / {n_valid} bar cua tap valid"


def test_evaluation_never_touches_the_test_split(fs, cfg):
    """Ho hang cua bat bien #5 va cua so ghi so lan nhin tap test."""
    from laplace.rl.evaluate import evaluate

    policy = Policy(n_features=fs.matrix().shape[1], window=cfg.window)
    out = evaluate(policy, fs, cfg, split="valid", device=torch.device("cpu"), seed=0)

    first, last = out["first_bar"], out["last_bar"]
    test_idx = np.flatnonzero(fs.split.test)
    assert last < test_idx.min(), "danh gia lan sang tap test"
    assert first >= np.flatnonzero(fs.split.valid).min()


def test_collect_bootstraps_from_the_pre_reset_state(fs, cfg):
    """Bat bien 18, ve quan trong nhat: `collect()` phai NAP dung gia tri bootstrap.

    Bai `test_boundary_bootstraps_instead_of_zeroing_future` chi kiem `compute_gae` voi
    dau vao dung, nen no KHONG bat duoc loi nap sai - va do dung la loi da xay ra that:
    sau khi mot moi truong tam dung roi duoc reset, `values[t+1]` la gia tri cua diem
    bat dau ngau nhien MOI, thuoc mot quy dao khac han. Phai dung V tinh truoc khi reset.
    """
    env = TradingEnv(fs, cfg, n_env=4, device=torch.device("cpu"), episode_len=8, seed=0)
    policy = Policy(n_features=fs.matrix().shape[1], window=cfg.window)
    tr = PPOTrainer(policy, env, PPOConfig(n_steps=12, n_epochs=1, minibatch=16),
                    device=torch.device("cpu"))
    batch = tr.collect()

    values, next_values = batch["value"], batch["next_value"]
    naive = torch.cat([values[1:], values[-1:]], dim=0)     # cach nap SAI
    truncated = batch["cut"][:-1]                           # bo ranh gioi cuoi rollout

    assert truncated.any(), "can it nhat mot lan tam dung de bai nay co y nghia"
    differs = (next_values[:-1] - naive[:-1]).abs() > 1e-6
    assert (differs & truncated).any(), (
        "tai bar tam dung, gia tri bootstrap van bang values[t+1] "
        "- dang lay trang thai sau khi reset")


def test_evaluation_restores_training_mode(fs, cfg):
    """`evaluate()` khong duoc de mang ket o che do eval.

    Neu quen tra lai, lan huan luyen ke tiep nem "cudnn RNN backward can only be called
    in training mode" - mot thong bao khong he tro toi cho that su sai. Da xay ra that.
    """
    from laplace.rl.evaluate import evaluate

    policy = Policy(n_features=fs.matrix().shape[1], window=cfg.window)
    policy.train()
    evaluate(policy, fs, cfg, split="valid", device=torch.device("cpu"), seed=0,
             max_bars=50)
    assert policy.training, "evaluate() de mang ket o che do eval"

    policy.eval()
    evaluate(policy, fs, cfg, split="valid", device=torch.device("cpu"), seed=0,
             max_bars=50)
    assert not policy.training, "evaluate() phai tra lai dung che do cu"
