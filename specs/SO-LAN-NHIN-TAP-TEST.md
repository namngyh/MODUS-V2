# Sổ ghi số lần nhìn tập test

CLAUDE.md nói *"mỗi lần nhìn tập test là một lần tiêu bớt giá trị của nó"*. Một lời nhắc
không có sổ ghi thì không kiểm chứng được — file này là sổ ghi đó.

**Tập test hiện tại** (từ spec 007, người dùng chốt 2026-09-28):
**2023-01-01 → hết dữ liệu (2026-09-04)**, bỏ 102 bar đệm ở đầu.

Ghi vào đây **mọi** lần dữ liệu sau `valid_end` được nhìn tới, kể cả khi chỉ là thống kê
mô tả và kể cả khi vô tình. Ghi cả những lần *không* dùng kết quả để quyết định gì —
điều quan trọng là số lần, không phải ý định.

## Trước khi đổi mốc: đoạn 2023–2026 đã được dùng hợp lệ

Trước spec 007, phần lớn đoạn 2023–2026 là **train và valid**. Nó đã được dùng hợp lệ
khi đó, nhưng với mốc mới thì đó là những lần nhìn vào tập test. Chưa có mô hình nào
được **chọn** dựa trên đoạn này; nhưng **cách xử lý dữ liệu** thì có.

| Việc | Đoạn đã dùng | Ảnh hưởng tới quyết định |
|---|---|---|
| Spec 004: so profit với reward theo năm trên lệnh KESPT | các năm tới 2025 | Quy ước từ vựng profit/reward — không đổi mô hình |
| Spec 005: ngưỡng nhiễu, 10 policy ngẫu nhiên | 2024-07 → 2025-06 | Không chọn mô hình; con số đã hết hiệu lực |
| Spec 006: đo độ trôi, **phát hiện nhà cung cấp đổi cách phân loại mua/bán năm 2023** | 2017-12 → 2025-06 | **Có**: thiết kế lớp `adaptive` cho dòng lệnh và xoá 4 cột sản phẩm phụ |
| Backtest hai bot trong README | 2017 → 2026 | Kiểm chứng bản dịch AFL — không đổi mô hình |
| Báo cáo `build_features.py` in số bar long/short của bot trên toàn bộ dữ liệu | 2017 → 2026 | Không. Từ spec 007 chỉ in trên train + valid |
| Đo giá của việc bỏ đảo chiều trên KESPT (2026-09-28) | 2017-12 → 2025-06 | Quy tắc không đảo chiều — người dùng đã chốt trước khi đo |
| Cấu hình ba repo phụ trợ (ARSH, Distributional BB, EGARCH-X) | các repo gốc chọn cấu hình khi có nhìn 2023–2026 | Cấu hình sẽ dùng lại; tham số học lại trên train của MODUS |

**Cách báo kết quả thi cuối** vì các lần trên: tách hai đoạn — **2023-01 → 2025-06** (đã
dùng khi thiết kế xử lý dữ liệu) và **2025-07 → 2026-09** (mới chỉ bị nhìn qua backtest
bot và báo cáo build).

## Sổ ghi

| # | Ngày | Ai / việc gì | Nhìn cái gì | Có dùng để quyết định không |
|---|---|---|---|---|
| 1 | 2026-09-06 | Claude, khảo sát open interest | Bảng 2×2 giá × ΔOI, thống kê mô tả trên **toàn bộ** 2017–2026 (gồm cả vùng test cũ) | **Không.** Phát hiện ngay, chạy lại giới hạn trong train, quyết định cuối cùng (chưa dùng OI) dựa trên train + valid |

## Quy tắc

- Đánh giá mô hình, chọn siêu tham số, so sánh nhánh thí nghiệm: **luôn dùng tập valid**
- Tập test chỉ mở đúng **một lần**, khi đã chốt hoàn toàn mô hình và không còn ý định sửa
- Nếu đã nhìn rồi mà vẫn sửa mô hình, thì kết quả test sau đó không còn là ước lượng
  không thiên lệch nữa — phải ghi rõ điều đó trong spec tương ứng
- Thăm dò dữ liệu (phân bố, chất lượng, giá trị thiếu) trên vùng test vẫn phải ghi vào
  đây, dù nó ít nguy hiểm hơn nhiều so với việc đo hiệu năng mô hình
