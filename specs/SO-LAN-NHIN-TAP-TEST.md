# Sổ ghi số lần nhìn tập test

CLAUDE.md nói *"mỗi lần nhìn tập test là một lần tiêu bớt giá trị của nó"*. Một lời nhắc
không có sổ ghi thì không kiểm chứng được — file này là sổ ghi đó.

**Tập test hiện tại**: 2025-07-03 → 2026-09-04, 14.304 bar.

Ghi vào đây **mọi** lần dữ liệu sau `valid_end` được nhìn tới, kể cả khi chỉ là thống kê
mô tả và kể cả khi vô tình. Ghi cả những lần *không* dùng kết quả để quyết định gì —
điều quan trọng là số lần, không phải ý định.

| # | Ngày | Ai / việc gì | Nhìn cái gì | Có dùng để quyết định không |
|---|---|---|---|---|
| 1 | 2026-09-06 | Claude, khảo sát open interest | Bảng 2×2 giá × ΔOI, thống kê mô tả trên **toàn bộ** 2017–2026 (gồm cả vùng test) | **Không.** Phát hiện ngay, chạy lại giới hạn trong train, và quyết định cuối cùng (chưa dùng OI) dựa trên số liệu train + valid |

## Quy tắc

- Đánh giá mô hình, chọn siêu tham số, so sánh nhánh thí nghiệm: **luôn dùng tập valid**
- Tập test chỉ mở đúng **một lần**, khi đã chốt hoàn toàn mô hình và không còn ý định sửa
- Nếu đã nhìn rồi mà vẫn sửa mô hình, thì kết quả test sau đó không còn là ước lượng
  không thiên lệch nữa — phải ghi rõ điều đó trong spec tương ứng
- Thăm dò dữ liệu (phân bố, chất lượng, giá trị thiếu) trên vùng test vẫn phải ghi vào
  đây, dù nó ít nguy hiểm hơn nhiều so với việc đo hiệu năng mô hình
