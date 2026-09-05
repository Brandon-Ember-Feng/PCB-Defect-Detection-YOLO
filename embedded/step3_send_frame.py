# -*- coding: utf-8 -*-
"""
第3步：电脑端模拟发送缺陷数据帧
帧格式：$ + 6组两位数量 + #
顺序：  鼠咬 缺孔 毛刺 短路 开路 多余铜
例：    $030100020000#  -> 鼠咬3 缺孔1 毛刺0 短路2 开路0 多余铜0
"""
import serial
import time

# ====== 改成你的CH340 COM号 ======
PORT = "COM3"
BAUD = 9600
# =================================

# 类别顺序（和51端一致）
CLASSES = ["鼠咬", "缺孔", "毛刺", "短路", "开路", "多余铜"]

def make_frame(counts):
    """counts: 6个整数 -> $030100020000# 字符串"""
    assert len(counts) == 6
    body = "".join(f"{c:02d}" for c in counts)
    return "$" + body + "#"

def send(ser, counts):
    frame = make_frame(counts)
    ser.write(frame.encode("ascii"))
    total = sum(counts)
    detail = " ".join(f"{CLASSES[i]}{counts[i]}" for i in range(6))
    print(f"发送 {frame}  共{total}个 | {detail}")

def main():
    try:
        ser = serial.Serial(PORT, BAUD, timeout=1)
    except Exception as e:
        print(f"[错误] 打不开{PORT}：{e}")
        return
    time.sleep(2)

    # 几组测试帧，每帧间隔4秒，观察LCD两行显示与第二行轮播
    test_frames = [
        [3, 1, 0, 2, 0, 0],   # 鼠咬3 缺孔1 短路2
        [0, 5, 2, 0, 1, 0],   # 缺孔5 毛刺2 开路1
        [1, 1, 1, 1, 1, 1],   # 每类各1
        [0, 0, 0, 0, 0, 0],   # 无缺陷
    ]
    for counts in test_frames:
        send(ser, counts)
        time.sleep(4)

    print("测试完成。LCD第一行显示总数，第二行每1.5秒轮播两类页。")
    ser.close()

if __name__ == "__main__":
    main()
