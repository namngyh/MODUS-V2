"""Trang thai vi the va chuyen trang thai theo hanh dong (spec 002 muc 2.2, 2.5).

Toan bo module vector hoa qua chieu moi truong: mot loi goi xu ly ca 512 moi truong
song song, khong co vong lap Python nao tren chieu do (xem muc "Uu tien GPU" trong
CLAUDE.md). Vong lap duy nhat trong huan luyen la vong lap theo THOI GIAN, va vong do
khong bo duoc vi vi the tai bar t+1 phu thuoc hanh dong tai bar t.
"""

from __future__ import annotations

import torch

# Hanh dong cua head ENTRY (dung khi FLAT, hoac ngay sau EXIT trong cung bar)
ENTRY_SKIP, ENTRY_LONG, ENTRY_SHORT = 0, 1, 2
# Hanh dong cua head EXIT (chi dung khi dang co lenh)
EXIT_HOLD, EXIT_EXIT = 0, 1

# 6 bien vi the + 4 so hang tuong tac. Tien to "pos_" la co y: no lam bat bien #14
# ("trang thai vi the khong bao gio nam trong features.npy") kiem tra duoc bang ten,
# va loai bo kha nang trung ten voi mot cot dac trung thi truong.
STATE_NAMES = (
    "pos_side", "pos_bars_held", "pos_pnl_atr", "pos_mfe_atr",
    "pos_retained", "pos_dist_stop",
    "pos_x_ret1", "pos_x_ret12", "pos_x_ret51", "pos_x_st_dist",
)
N_POSITION_VARS, N_INTERACTION = 6, 4
N_STATE = N_POSITION_VARS + N_INTERACTION
assert len(STATE_NAMES) == N_STATE

# Anh xa hanh dong entry -> vi the muc tieu
_ENTRY_TO_POS = torch.tensor([0, 1, -1], dtype=torch.int8)


def _signed_log1p(x: torch.Tensor) -> torch.Tensor:
    """Nen dai luong khong chan ve thang do cua cac dau vao con lai.

    454 dac trung deu da qua RobustScaler va cat o +-8. Cac bien vi the thi tho: do
    tren 1.539 lenh cua KESPT, `mfe_atr` len toi **80 lan ATR** (99% o 39,7). Mot dau
    vao lon gap muoi lan moi dau vao khac se at het phan con lai ngay tu buoc khoi tao.

        1 ATR -> 0,69      10 ATR -> 2,40
        3 ATR -> 1,39      40 ATR -> 3,71
        5 ATR -> 1,79      80 ATR -> 4,39

    Chon log thay vi tanh vi tanh bao hoa: 5 va 80 ATR deu thanh ~1, ma 42,5% so lenh
    nam tren 5 ATR nen mat mat la that. Log nen diu va khong bao gio bao hoa.
    """
    return torch.sign(x) * torch.log1p(x.abs())


def resolve_actions(
    position: torch.Tensor, entry_action: torch.Tensor, exit_action: torch.Tensor
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """Hanh dong ghep: giai ra vi the moi va cho biet head nao da duoc dung.

    Ca hai head deu duoc lay mau o moi bar, nhung chi mot phan duoc *dung*:

        FLAT              -> dung head entry
        co lenh + HOLD    -> dung head exit, vi the khong doi
        co lenh + EXIT    -> dung CA HAI: exit quyet dinh thoat, roi entry quyet dinh
                             chieu moi ngay trong cung bar (dao chieu trong 1 bar)

    Tra ve (vi the moi, mask da dung head entry, mask da dung head exit). Hai mask nay
    la thu quyet dinh so hang nao vao log-prob cua PPO.
    """
    flat = position == 0
    used_exit = ~flat
    exiting = used_exit & (exit_action == EXIT_EXIT)
    used_entry = flat | exiting

    target = _ENTRY_TO_POS.to(position.device)[entry_action]
    new_position = torch.where(used_entry, target, position)
    return new_position, used_entry, used_exit


class PositionState:
    """Vi the dang mo cua N moi truong song song.

    Thu tu goi trong mot buoc moi truong:

        state.advance(price)                      # gia moi -> cap nhat bars_held, MFE
        sv = state.state_vector(price, direct)    # dua vao mang
        ... mang chon hanh dong ...
        state.apply(entry_a, exit_a, price, atr)  # chuyen trang thai
    """

    def __init__(self, n_env: int, device: torch.device | str = "cpu",
                 session_bars: int = 51, stop_atr_mult: float = 2.0):
        self.n_env = n_env
        self.device = torch.device(device)
        self.session_bars = float(session_bars)
        self.stop_atr_mult = float(stop_atr_mult)

        z = lambda dtype: torch.zeros(n_env, dtype=dtype, device=self.device)
        self.position = z(torch.int8)
        self.entry_price = z(torch.float32)
        # Mau so cua moi bien chuan hoa. Chot tai bar vao lenh va giu nguyen suot lenh:
        # neu dung ATR hien tai, bien vi the se nhay khi thi truong doi che do bien dong
        # chu khong phai khi lenh thay doi.
        self.entry_atr = torch.ones(n_env, dtype=torch.float32, device=self.device)
        self.bars_held = z(torch.int32)
        self.mfe_atr = z(torch.float32)

    # ------------------------------------------------------------------ #
    def reset(self, mask: torch.Tensor | None = None) -> None:
        """Dong vi the va xoa trang thai. `mask` = None nghia la reset tat ca."""
        if mask is None:
            mask = torch.ones(self.n_env, dtype=torch.bool, device=self.device)
        self.position = torch.where(mask, torch.zeros_like(self.position), self.position)
        self.entry_price = torch.where(mask, torch.zeros_like(self.entry_price),
                                       self.entry_price)
        self.entry_atr = torch.where(mask, torch.ones_like(self.entry_atr), self.entry_atr)
        self.bars_held = torch.where(mask, torch.zeros_like(self.bars_held), self.bars_held)
        self.mfe_atr = torch.where(mask, torch.zeros_like(self.mfe_atr), self.mfe_atr)

    def pnl_atr(self, price: torch.Tensor) -> torch.Tensor:
        """Lai lo chua thuc hien, tinh bang so lan ATR. Bang 0 khi dang FLAT."""
        raw = self.position.to(price.dtype) * (price - self.entry_price) / self.entry_atr
        return torch.where(self.position != 0, raw, torch.zeros_like(raw))

    def advance(self, price: torch.Tensor) -> None:
        """Sang bar moi: tang so bar da giu va cap nhat dinh lai (MFE).

        MFE la dinh CHAY cua pnl trong lenh nay, khong phai pnl hien tai. Nham hai cai
        nay thi `retained` luon bang 1 va mat hoan toan y nghia trailing stop.
        """
        live = self.position != 0
        self.bars_held = self.bars_held + live.to(self.bars_held.dtype)
        self.mfe_atr = torch.where(live, torch.maximum(self.mfe_atr, self.pnl_atr(price)),
                                   self.mfe_atr)

    def apply(self, entry_action: torch.Tensor, exit_action: torch.Tensor,
              price: torch.Tensor, atr: torch.Tensor) -> torch.Tensor:
        """Ap hanh dong, mo/dong lenh, tra ve vi the moi."""
        new_position, _, _ = resolve_actions(self.position, entry_action, exit_action)

        # Mo lenh moi = vi the khac 0 va khac vi the cu. Bao gom ca dao chieu, nen cac
        # bien cua lenh cu phai bi xoa sach chu khong duoc thua ke.
        opened = (new_position != 0) & (new_position != self.position)
        closed = (new_position == 0) & (self.position != 0)

        self.entry_price = torch.where(opened, price, self.entry_price)
        self.entry_atr = torch.where(opened, atr.clamp(min=1e-6), self.entry_atr)
        wipe = opened | closed
        self.bars_held = torch.where(wipe, torch.zeros_like(self.bars_held), self.bars_held)
        self.mfe_atr = torch.where(wipe, torch.zeros_like(self.mfe_atr), self.mfe_atr)
        self.position = new_position
        return new_position

    # ------------------------------------------------------------------ #
    def state_vector(self, price: torch.Tensor, directional: torch.Tensor) -> torch.Tensor:
        """Ghep 10 so dua vao sau encoder: 6 bien vi the + 4 so hang tuong tac.

        `directional` la (N, 4) gom cac dac trung CO CHIEU lay tu ma tran dac trung:
        ret1, ret12, ret51, kespt_st_dist_atr. Chung duoc nhan voi dau vi the de head
        exit nhin thi truong "tu goc cua lenh dang cam" - nho vay no chi phai hoc mot
        ham thay vi hai ham rieng cho long va short.

        Khong nhan ca `h_t` voi dau vi the: `h_t` tron lan dai luong co chieu (return)
        voi dai luong khong chieu (bien dong, bien do - luon duong), nhan -1 se sua cai
        thu nhat va pha cai thu hai.
        """
        live = self.position != 0
        pos = self.position.to(price.dtype)
        pnl = self.pnl_atr(price)

        # Con giu bao nhieu phan loi nhuan dinh, chan trong [-1, 1] va KHONG can quy uoc
        # nao cho truong hop suy bien. Mau so lay max cua ba thu:
        #   MFE > |pnl|  -> pnl/MFE, dung nghia "con giu bao nhieu phan dinh"
        #   |pnl| >= MFE -> +-1, nghia la "dang o diem tot/te nhat cua lenh nay"
        # Lenh chua tung co lai (MFE = 0) tu roi vao nhanh thu hai va ra -1, dung nghia
        # chu khong phai mot con so gan ep. Do tren 1.539 lenh cua KESPT: 9,3% so lenh
        # chua tung co lai, nen truong hop nay khong hiem.
        denom = torch.maximum(torch.maximum(self.mfe_atr, pnl.abs()),
                              torch.full_like(pnl, 1e-9))
        retained = pnl / denom

        # Moc dung lo tham chieu, chi de DO KHOANG CACH - khong phai lenh dung lo that
        # duoc thuc thi. Agent van tu quyet dinh thoat.
        stop = self.entry_price - pos * self.stop_atr_mult * self.entry_atr
        dist_stop = pos * (price - stop) / self.entry_atr

        vars_ = torch.stack([
            pos,
            self.bars_held.to(price.dtype) / self.session_bars,
            _signed_log1p(pnl),
            _signed_log1p(self.mfe_atr),
            retained,
            _signed_log1p(dist_stop),
        ], dim=1)
        # FLAT thi moi bien vi the deu vo nghia -> khong dua so rac vao mang.
        vars_ = vars_ * live.unsqueeze(1).to(price.dtype)

        return torch.cat([vars_, directional * pos.unsqueeze(1)], dim=1)
