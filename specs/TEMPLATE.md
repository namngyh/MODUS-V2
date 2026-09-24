# NNN — <tên ngắn>

- **Trạng thái**: nháp | đã thống nhất | đang làm | xong | **bị bác**
- **Ngày**: YYYY-MM-DD
- **Ảnh hưởng tới**: <file / nhóm đặc trưng / bất biến số mấy>

## 1. Câu hỏi

Một hai câu: làm cái gì, và tại sao là bây giờ. Nếu không viết nổi trong hai câu thì
spec này đang gộp nhiều việc — tách ra.

## 2. Đầu vào → đầu ra

| | Thứ gì | Đơn vị |
|---|---|---|
| Vào | | |
| Ra | | |

Đơn vị là bắt buộc. Phần lớn lỗi trong repo này là lỗi đơn vị: mức giá lẫn với chênh
lệch giá, phần trăm lẫn với tỷ lệ, tổng luỹ kế lẫn với biến thiên.

## 3. Lập luận nhân quả

Tại sao giá trị tại *t* chỉ dùng dữ liệu ≤ *t*. Nêu rõ mọi cửa sổ trượt, mọi phép
`shift`, mọi tham số ước lượng và tập nào dùng để ước lượng.

Nếu có gì đó nhìn tới tương lai một cách có chủ ý (ví dụ nhãn), nói rõ ở đây bao nhiêu
bar, và cách những bar đó bị loại khỏi tập cửa sổ.

## 4. Bất biến

Bất biến mới cần thêm vào bảng trong CLAUDE.md, hoặc bất biến hiện có bị ảnh hưởng.
Ghi "không" nếu không có.

## 5. Bài test làm spec này thất bại

```
tests/<file>.py::<tên hàm test>
```

Mô tả một câu: nếu triển khai sai thì test này đỏ *như thế nào*. Bắt buộc phải có. Một
spec không nêu được cách chứng minh mình sai thì không phải spec, chỉ là ý định.

## 6. Tiêu chí chấp nhận

Quyết định **trước khi chạy**:

- Dùng tập nào để đánh giá:
- Ngưỡng nào là thành công:
- Đã nhìn vào tập test bao nhiêu lần trước khi viết spec này:

Với thay đổi thuần kỹ thuật (không có giả thuyết thị trường), ghi tiêu chí kỹ thuật:
thời gian chạy, bộ nhớ, số cột, test nào phải xanh.

---

## Kết quả

*Điền sau khi làm xong. Ghi cả khi thất bại — đó là phần có giá trị nhất của file này.*

- Đã làm gì:
- Số liệu thực tế so với tiêu chí ở mục 6:
- Kết luận: chấp nhận / bác bỏ / cần thêm dữ liệu
- Nếu bác bỏ: **đừng xoá file này.** Đổi trạng thái thành "bị bác" và ghi lý do, để lần
  sau không ai chạy lại cùng một ý tưởng.
