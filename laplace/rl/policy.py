"""Mang policy: mot encoder dung chung, hai head hanh dong, mot head gia tri (spec 002).

Kien truc va ly do chon tung con so nam o specs/002-cau-truc-policy.md. Tom tat:

    454 dac trung x 64 bar
        -> Linear(454 -> 64) + tanh     29.120 tham so   (87% tham so cua LSTM truc
                                                          tiep nam o ma tran dau vao,
                                                          nen chieu truoc la cach re
                                                          nhat de cat mot nua)
        -> LSTM(64 -> 64), 1 lop        33.280
        -> h_t (64) ghep 10 so trang thai vi the
        -> ENTRY(3) | EXIT(2) | VALUE(1)  moi cai ~4.900
                                        tong 77.190

Ngan sach: 83.025 cua so train nhung chi 1.297 khoi 64-bar doc lap, nen moi tham so
deu phai tra gia.
"""

from __future__ import annotations

from dataclasses import dataclass

import torch
import torch.nn as nn

from .state import N_STATE, resolve_actions


@dataclass
class ActOutput:
    """Ket qua mot buoc quyet dinh cho ca lo moi truong."""

    position: torch.Tensor       # (N,) int8 - vi the sau khi ap hanh dong
    entry_action: torch.Tensor   # (N,) int64 - SKIP / LONG / SHORT
    exit_action: torch.Tensor    # (N,) int64 - HOLD / EXIT
    used_entry: torch.Tensor     # (N,) bool - head entry co duoc dung o bar nay khong
    used_exit: torch.Tensor      # (N,) bool
    log_prob: torch.Tensor       # (N,) float - tong log-prob cua cac head DA dung
    entropy: torch.Tensor        # (N,) float
    value: torch.Tensor          # (N,) float


def _mlp_head(in_dim: int, out_dim: int, hidden: int = 64) -> nn.Sequential:
    return nn.Sequential(nn.Linear(in_dim, hidden), nn.ReLU(), nn.Linear(hidden, out_dim))


class Policy(nn.Module):
    def __init__(self, n_features: int, window: int, proj_dim: int = 64,
                 hidden: int = 64, n_state: int = N_STATE):
        super().__init__()
        self.n_features, self.window = n_features, window
        self.proj = nn.Linear(n_features, proj_dim)
        self.lstm = nn.LSTM(proj_dim, hidden, num_layers=1, batch_first=True)

        head_in = hidden + n_state
        self.entry = _mlp_head(head_in, 3)
        self.exit = _mlp_head(head_in, 2)
        self.value = _mlp_head(head_in, 1)

    # ------------------------------------------------------------------ #
    def encode(self, x: torch.Tensor) -> torch.Tensor:
        """(N, window, n_features) -> h_t (N, hidden).

        Doc lai ca cua so o moi buoc (cach A trong spec 002 muc 2.4): tri nho luon dung
        64 bar, khong phu thuoc vi tri trong episode.
        """
        out, _ = self.lstm(torch.tanh(self.proj(x)))
        return out[:, -1]

    def logits(self, x: torch.Tensor, state_vec: torch.Tensor):
        h = torch.cat([self.encode(x), state_vec], dim=-1)
        return self.entry(h), self.exit(h), self.value(h).squeeze(-1)

    # ------------------------------------------------------------------ #
    def act(self, x: torch.Tensor, state_vec: torch.Tensor, position: torch.Tensor,
            deterministic: bool = False) -> ActOutput:
        """Lay mau hanh dong cho ca lo.

        Lay mau CA HAI head o moi bar roi mask - khong phai vi phi pham, ma vi mot bar
        dao chieu can ca hai, va lam vay thi khong co vong lap Python nao tren chieu
        moi truong.
        """
        entry_logits, exit_logits, value = self.logits(x, state_vec)
        entry_dist = torch.distributions.Categorical(logits=entry_logits)
        exit_dist = torch.distributions.Categorical(logits=exit_logits)

        if deterministic:
            entry_a, exit_a = entry_logits.argmax(-1), exit_logits.argmax(-1)
        else:
            entry_a, exit_a = entry_dist.sample(), exit_dist.sample()

        new_position, used_entry, used_exit = resolve_actions(position, entry_a, exit_a)
        zero = torch.zeros_like(value)

        # Log-prob cua mot bar la TONG cua cac head da duoc dung. Bar dao chieu dung ca
        # hai nen co hai so hang; chi lay mot se lam PPO tinh sai ty le importance ma
        # khong bao loi gi.
        log_prob = (torch.where(used_entry, entry_dist.log_prob(entry_a), zero)
                    + torch.where(used_exit, exit_dist.log_prob(exit_a), zero))
        entropy = (torch.where(used_entry, entry_dist.entropy(), zero)
                   + torch.where(used_exit, exit_dist.entropy(), zero))

        return ActOutput(new_position, entry_a, exit_a, used_entry, used_exit,
                         log_prob, entropy, value)

    def evaluate_actions(self, x: torch.Tensor, state_vec: torch.Tensor,
                         position: torch.Tensor, entry_action: torch.Tensor,
                         exit_action: torch.Tensor):
        """log-prob, entropy va gia tri cho hanh dong DA chon - mot luot forward.

        Dung o pha cap nhat cua PPO. Goi rieng `action_log_probs`, `logits` va `act` se
        chay ba luot forward cho cung mot minibatch, tot gap ba lan ma khong duoc gi.

        Chi cong so hang cua cac head DA duoc dung: bar dao chieu co hai so hang, bar
        HOLD chi co mot (spec 002).
        """
        entry_logits, exit_logits, value = self.logits(x, state_vec)
        entry_dist = torch.distributions.Categorical(logits=entry_logits)
        exit_dist = torch.distributions.Categorical(logits=exit_logits)

        _, used_entry, used_exit = resolve_actions(position, entry_action, exit_action)
        zero = torch.zeros_like(value)
        log_prob = (torch.where(used_entry, entry_dist.log_prob(entry_action), zero)
                    + torch.where(used_exit, exit_dist.log_prob(exit_action), zero))
        entropy = (torch.where(used_entry, entry_dist.entropy(), zero)
                   + torch.where(used_exit, exit_dist.entropy(), zero))
        return log_prob, entropy, value

    def action_log_probs(self, x: torch.Tensor, state_vec: torch.Tensor,
                         position: torch.Tensor, entry_action: torch.Tensor,
                         exit_action: torch.Tensor):
        """Log-prob rieng cua tung head cho hanh dong da chon.

        Dung o pha cap nhat cua PPO, khi phai tinh lai log-prob cua hanh dong cu duoi
        policy moi. Tra ve rieng hai so hang de goi ben ngoai tu quyet dinh cong cai nao.
        """
        entry_logits, exit_logits, _ = self.logits(x, state_vec)
        entry_logp = torch.distributions.Categorical(logits=entry_logits).log_prob(entry_action)
        exit_logp = torch.distributions.Categorical(logits=exit_logits).log_prob(exit_action)
        return entry_logp, exit_logp

    def n_parameters(self) -> int:
        return sum(p.numel() for p in self.parameters())
