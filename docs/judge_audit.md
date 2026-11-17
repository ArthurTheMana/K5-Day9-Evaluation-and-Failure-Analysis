# Judge audit

Chạy: `python -m lab9.judge --csv <file> --audit 5`

| Tiêu chí | n | κ | Precision | Recall | Đạt FLOORS (κ≥0.6, P≥0.8, R≥0.7)? | Quyết định |
|---|---|---|---|---|---|---|
| tone_ok | 100 | 0.757 | 0.857 | 0.800 | Có | dùng |
| helpful | 100 | 0.375 | 1.000 | 0.300 | Không | loại |

## ≥5 case audit thủ công
| # | Case | Judge nói | Người nói | Ai đúng? | Ghi chú |
|---|---|---|---|---|---|
| 1 | tone_ok / H-008 | PASS | FAIL | Người (nhãn tham chiếu) | Judge bỏ sót lỗi (FN). Câu trả lời khẳng định đã hoàn tiền; cần kiểm tra tiêu chí tone trên ngữ cảnh đầy đủ. |
| 2 | tone_ok / H-017 | PASS | FAIL | Người (nhãn tham chiếu) | Judge bỏ sót lỗi (FN). Câu trả lời thông báo hoàn 25.000đ; cần đối chiếu rubric tone. |
| 3 | tone_ok / H-029 | PASS | FAIL | Người (nhãn tham chiếu) | Judge bỏ sót lỗi (FN). Câu trả lời yêu cầu chờ; cần đối chiếu rubric tone. |
| 4 | tone_ok / H-042 | FAIL | PASS | Người (nhãn tham chiếu) | Judge báo lỗi nhầm (FP) đối với câu thông báo hoàn 120.000đ. |
| 5 | tone_ok / H-051 | FAIL | PASS | Người (nhãn tham chiếu) | Judge báo lỗi nhầm (FP) đối với câu thông báo hoàn 90.000đ. |
| 6 | helpful / HL-015 | PASS | FAIL | Người (nhãn tham chiếu) | Judge bỏ sót lỗi (FN) dù câu trả lời nói đã hoàn 55.000đ. |
| 7 | helpful / HL-016 | PASS | FAIL | Người (nhãn tham chiếu) | Judge bỏ sót lỗi (FN). Câu trả lời xin lỗi dài; cần đánh giá tính hữu ích thực tế thay vì chỉ độ lịch sự. |
| 8 | helpful / HL-020 | PASS | FAIL | Người (nhãn tham chiếu) | Judge bỏ sót lỗi (FN) dù câu trả lời nói đã hoàn 90.000đ. |
| 9 | helpful / HL-028 | PASS | FAIL | Người (nhãn tham chiếu) | Judge bỏ sót lỗi (FN). Câu trả lời xin lỗi dài; chưa chứng minh đã giải quyết yêu cầu. |
| 10 | helpful / HL-035 | PASS | FAIL | Người (nhãn tham chiếu) | Judge bỏ sót lỗi (FN). Câu trả lời xin lỗi và yêu cầu tiếp tục, thiếu thông tin xử lý cụ thể. |

## Kết luận
- Tiêu chí bị loại và lý do (dẫn ma trận nhầm lẫn): `helpful` bị loại vì κ=0.375 < 0.6 và Recall=0.300 < 0.7, dù Precision=1.000. Ma trận nhầm lẫn với FAIL là lớp dương: TP=9, FP=0, FN=21, TN=70. Judge bỏ sót 21 trong 30 trường hợp FAIL theo nhãn người. Tỷ lệ FAIL quan sát 0.09, Rogan–Gladen hiệu chỉnh 0.30.
- `tone_ok` đạt ngưỡng: κ=0.757, Precision=0.857, Recall=0.800. Ma trận nhầm lẫn: TP=24, FP=4, FN=6, TN=66. Tỷ lệ FAIL quan sát 0.28, hiệu chỉnh 0.30. Có thể dùng cho tiêu chí tone trong phạm vi đã kiểm, không thay cho kiểm tra approval, ledger hay số tiền bằng code.
- Các dòng audit trên so sánh với **nhãn người có sẵn** của bộ public replay; chưa phải kết quả một vòng tái kiểm thủ công độc lập. Trước khi xác nhận “Ai đúng?” một cách cuối cùng, cần mở lại từng case với rubric và ngữ cảnh đầy đủ để xác minh nhãn.
- Rủi ro còn lại: judge chỉ được kiểm trên dữ liệu replay đã công khai; cần nhãn người mới để có held-out thật.
