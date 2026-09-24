"""Canh spec 002 - cau truc policy hai head.

Bai test quan trong nhat o day la `test_compound_log_prob_is_sum_of_both_steps`. Neu
sai, PPO khong crash, khong bao gi ca - no chi tinh sai ty le importance va hoc lech.
Do la kieu loi ma chi co test moi bat duoc.
"""

from __future__ import annotations

import numpy as np
import pytest
import torch

from laplace.rl.policy import Policy
from laplace.rl.state import (
    ENTRY_LONG,
    ENTRY_SHORT,
    ENTRY_SKIP,
    EXIT_EXIT,
    EXIT_HOLD,
    N_STATE,
    PositionState,
    resolve_actions,
)

N_FEAT, WINDOW, N_ENV = 454, 64, 8


@pytest.fixture
def state() -> PositionState:
    return PositionState(N_ENV, device=torch.device("cpu"))


# --------------------------------------------------------------------------- #
# Chuyen trang thai - logic thuan, khong dinh mang
# --------------------------------------------------------------------------- #
def test_entry_head_used_only_when_flat():
    pos = torch.tensor([0, 0, 1, -1, 0, 1, -1, 0], dtype=torch.int8)
    entry = torch.full((8,), ENTRY_LONG, dtype=torch.int64)
    exit_ = torch.full((8,), EXIT_HOLD, dtype=torch.int64)

    new_pos, used_entry, used_exit = resolve_actions(pos, entry, exit_)
    # Dang giu lenh va chon HOLD -> head entry khong duoc dung
    torch.testing.assert_close(used_entry, pos == 0)


def test_exit_head_used_only_when_in_position():
    pos = torch.tensor([0, 0, 1, -1, 0, 1, -1, 0], dtype=torch.int8)
    entry = torch.full((8,), ENTRY_SKIP, dtype=torch.int64)
    exit_ = torch.full((8,), EXIT_HOLD, dtype=torch.int64)

    _, _, used_exit = resolve_actions(pos, entry, exit_)
    torch.testing.assert_close(used_exit, pos != 0)


def test_compound_action_reverses_within_one_bar():
    """Dang LONG, chon EXIT roi head entry chon SHORT -> SHORT ngay trong bar nay."""
    pos = torch.tensor([1, 1, -1, 0], dtype=torch.int8)
    entry = torch.tensor([ENTRY_SHORT, ENTRY_SKIP, ENTRY_LONG, ENTRY_LONG])
    exit_ = torch.tensor([EXIT_EXIT, EXIT_EXIT, EXIT_EXIT, EXIT_HOLD])

    new_pos, used_entry, used_exit = resolve_actions(pos, entry, exit_)

    assert new_pos[0].item() == -1, "LONG + EXIT + SHORT phai dao chieu trong 1 bar"
    assert new_pos[1].item() == 0, "LONG + EXIT + SKIP phai ve FLAT"
    assert new_pos[2].item() == 1, "SHORT + EXIT + LONG phai dao chieu trong 1 bar"
    assert new_pos[3].item() == 1, "FLAT + LONG phai vao lenh"
    # Bar dao chieu dung ca hai head
    assert used_entry[0] and used_exit[0]


def test_hold_keeps_position_and_increments_bars_held(state):
    price = torch.full((N_ENV,), 1000.0)
    atr = torch.full((N_ENV,), 5.0)
    entry = torch.full((N_ENV,), ENTRY_LONG, dtype=torch.int64)
    hold = torch.full((N_ENV,), EXIT_HOLD, dtype=torch.int64)
    skip = torch.full((N_ENV,), ENTRY_SKIP, dtype=torch.int64)

    state.apply(entry, torch.zeros_like(hold), price, atr)      # vao LONG
    assert (state.position == 1).all()
    assert (state.bars_held == 0).all()

    for step in range(1, 4):
        state.advance(price + step)
        state.apply(skip, hold, price + step, atr)
        assert (state.position == 1).all(), "HOLD khong duoc doi vi the"
        assert (state.bars_held == step).all(), f"bars_held sai o buoc {step}"


def test_mfe_never_decreases_within_a_trade(state):
    """MFE la dinh chay, khong phai lai lo hien tai."""
    atr = torch.full((N_ENV,), 4.0)
    entry = torch.full((N_ENV,), ENTRY_LONG, dtype=torch.int64)
    hold = torch.full((N_ENV,), EXIT_HOLD, dtype=torch.int64)
    skip = torch.full((N_ENV,), ENTRY_SKIP, dtype=torch.int64)

    state.apply(entry, torch.zeros_like(hold), torch.full((N_ENV,), 1000.0), atr)

    seen = []
    for px in (1004.0, 1012.0, 1006.0, 1002.0, 1010.0):
        p = torch.full((N_ENV,), px)
        state.advance(p)
        state.apply(skip, hold, p, atr)
        seen.append(state.mfe_atr.clone())

    # Ghep cap lien tiep, nen ve sau ngan hon mot phan tu - khong dung strict o day.
    for a, b in zip(seen, seen[1:]):
        assert (b >= a - 1e-6).all(), "MFE khong duoc giam trong cung mot lenh"
    # dinh la 1012 -> (1012-1000)/4 = 3.0
    assert seen[-1][0].item() == pytest.approx(3.0, abs=1e-5)


def test_position_state_resets_on_new_trade(state):
    atr = torch.full((N_ENV,), 5.0)
    long_ = torch.full((N_ENV,), ENTRY_LONG, dtype=torch.int64)
    short_ = torch.full((N_ENV,), ENTRY_SHORT, dtype=torch.int64)
    hold = torch.full((N_ENV,), EXIT_HOLD, dtype=torch.int64)
    exit_ = torch.full((N_ENV,), EXIT_EXIT, dtype=torch.int64)

    state.apply(long_, torch.zeros_like(hold), torch.full((N_ENV,), 1000.0), atr)
    for px in (1010.0, 1020.0):
        p = torch.full((N_ENV,), px)
        state.advance(p)
        state.apply(torch.full_like(long_, ENTRY_SKIP), hold, p, atr)
    assert state.mfe_atr[0].item() > 0 and state.bars_held[0].item() == 2

    # Dao chieu sang SHORT: moi thu phai reset cho lenh moi
    p = torch.full((N_ENV,), 1020.0)
    state.apply(short_, exit_, p, atr)
    assert (state.position == -1).all()
    assert (state.bars_held == 0).all(), "bars_held phai reset khi mo lenh moi"
    assert (state.mfe_atr == 0).all(), "MFE phai reset khi mo lenh moi"
    assert (state.entry_price == 1020.0).all()


def test_interaction_terms_flip_sign_with_position(state):
    """So hang tuong tac phai doi dau theo chieu lenh - do la ca muc dich cua chung."""
    atr = torch.full((N_ENV,), 5.0)
    px = torch.full((N_ENV,), 1000.0)
    directional = torch.randn(N_ENV, 4)

    state.apply(torch.full((N_ENV,), ENTRY_LONG, dtype=torch.int64),
                torch.zeros(N_ENV, dtype=torch.int64), px, atr)
    v_long = state.state_vector(px, directional)

    state.reset()
    state.apply(torch.full((N_ENV,), ENTRY_SHORT, dtype=torch.int64),
                torch.zeros(N_ENV, dtype=torch.int64), px, atr)
    v_short = state.state_vector(px, directional)

    torch.testing.assert_close(v_long[:, -4:], -v_short[:, -4:])


def test_position_state_variables_are_scale_free(state):
    """Cung mot lenh o hai vung gia khac nhau phai cho vector trang thai giong het.

    Neu quen chia ATR, bien vi the mang don vi diem va se doi thang do giua nam 2018
    (gia ~900) va 2026 (gia ~1900).
    """
    zero = torch.zeros(N_ENV, dtype=torch.int64)
    long_ = torch.full((N_ENV,), ENTRY_LONG, dtype=torch.int64)
    d = torch.zeros(N_ENV, 4)

    # Kich ban 1: gia 900, ATR 3, chay len 6 diem = 2 ATR
    state.apply(long_, zero, torch.full((N_ENV,), 900.0), torch.full((N_ENV,), 3.0))
    p1 = torch.full((N_ENV,), 906.0)
    state.advance(p1)
    v1 = state.state_vector(p1, d)

    # Kich ban 2: gia 1900, ATR 15, chay len 30 diem = cung 2 ATR
    state.reset()
    state.apply(long_, zero, torch.full((N_ENV,), 1900.0), torch.full((N_ENV,), 15.0))
    p2 = torch.full((N_ENV,), 1930.0)
    state.advance(p2)
    v2 = state.state_vector(p2, d)

    torch.testing.assert_close(v1, v2)


# --------------------------------------------------------------------------- #
# Mang
# --------------------------------------------------------------------------- #
def test_compound_log_prob_is_sum_of_both_steps():
    """Bar co dao chieu: log-prob phai la TONG cua hai buoc.

    Chi lay log-prob mot buoc thi PPO tinh sai ty le importance va cap nhat lech ma
    khong he bao loi.
    """
    torch.manual_seed(0)
    policy = Policy(n_features=N_FEAT, window=WINDOW)
    x = torch.randn(4, WINDOW, N_FEAT)
    sv = torch.randn(4, N_STATE)
    pos = torch.tensor([0, 1, -1, 1], dtype=torch.int8)

    out = policy.act(x, sv, pos, deterministic=True)
    entry_logp, exit_logp = policy.action_log_probs(x, sv, pos, out.entry_action,
                                                    out.exit_action)

    expected = torch.where(out.used_entry, entry_logp, torch.zeros_like(entry_logp))
    expected = expected + torch.where(out.used_exit, exit_logp, torch.zeros_like(exit_logp))
    torch.testing.assert_close(out.log_prob, expected)

    # Voi bar dao chieu, log_prob phai la tong hai so hang khac 0
    compound = out.used_entry & out.used_exit
    if compound.any():
        i = int(torch.nonzero(compound)[0])
        assert out.log_prob[i].item() == pytest.approx(
            entry_logp[i].item() + exit_logp[i].item(), abs=1e-5)


def test_policy_runs_on_gpu_when_available():
    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    policy = Policy(n_features=N_FEAT, window=WINDOW).to(dev)
    x = torch.randn(16, WINDOW, N_FEAT, device=dev)
    sv = torch.randn(16, N_STATE, device=dev)
    pos = torch.zeros(16, dtype=torch.int8, device=dev)

    out = policy.act(x, sv, pos)
    assert out.log_prob.device.type == dev.type
    assert out.value.shape == (16,)
    assert torch.isfinite(out.log_prob).all()


def test_parameter_budget_stays_small():
    """Ngan sach: 1.297 khoi doc lap. Moi tham so deu phai tra gia."""
    policy = Policy(n_features=N_FEAT, window=WINDOW)
    n = sum(p.numel() for p in policy.parameters())
    assert n <= 100_000, f"mang phinh len {n:,} tham so"


def test_retained_is_bounded_without_any_convention(state):
    """`retained` phai nam trong [-1, 1] o MOI tinh huong, ke ca lenh chua tung co lai.

    Do tren 1.539 lenh cua KESPT: 9,3% so lenh khong bao gio co lai, nen nhanh MFE = 0
    khong phai truong hop hiem gap ma phai xu ly cho co.
    """
    zero = torch.zeros(N_ENV, dtype=torch.int64)
    long_ = torch.full((N_ENV,), ENTRY_LONG, dtype=torch.int64)
    d = torch.zeros(N_ENV, 4)
    atr = torch.full((N_ENV,), 5.0)

    # Lenh lo ngay tu dau: MFE khong bao gio vuot 0
    state.apply(long_, zero, torch.full((N_ENV,), 1000.0), atr)
    for px in (995.0, 990.0, 985.0):
        p = torch.full((N_ENV,), px)
        state.advance(p)
        v = state.state_vector(p, d)
        r = v[:, 4]
        assert (r >= -1.0 - 1e-6).all() and (r <= 1.0 + 1e-6).all()
        assert r[0].item() == pytest.approx(-1.0, abs=1e-5), \
            "dang o day sau nhat cua lenh -> phai bang -1"

    # Lenh co lai roi tra lai mot nua
    state.reset()
    state.apply(long_, zero, torch.full((N_ENV,), 1000.0), atr)
    for px in (1020.0, 1010.0):
        p = torch.full((N_ENV,), px)
        state.advance(p)
    v = state.state_vector(torch.full((N_ENV,), 1010.0), d)
    assert v[0, 4].item() == pytest.approx(0.5, abs=1e-5), "giu lai 1/2 dinh -> 0,5"


def test_unbounded_state_vars_are_squashed(state):
    """pnl, MFE va dist_stop phai duoc nen ve thang do cua cac dau vao con lai."""
    zero = torch.zeros(N_ENV, dtype=torch.int64)
    long_ = torch.full((N_ENV,), ENTRY_LONG, dtype=torch.int64)
    d = torch.zeros(N_ENV, 4)
    atr = torch.full((N_ENV,), 1.0)

    # Lai 80 ATR - dung bang muc lon nhat do duoc tren lenh cua KESPT
    state.apply(long_, zero, torch.full((N_ENV,), 1000.0), atr)
    p = torch.full((N_ENV,), 1080.0)
    state.advance(p)
    v = state.state_vector(p, d)

    assert v[0, 2].item() == pytest.approx(np.log1p(80.0), abs=1e-4)
    assert v[0, 3].item() == pytest.approx(np.log1p(80.0), abs=1e-4)
    assert v[:, :6].abs().max().item() < 8.0, "moi bien vi the phai nam trong thang +-8"
