# -*- coding: utf-8 -*-
"""
最终界面 电脑端模拟：循环发送 待机->检测中->合格/不合格(单/多缺陷)
协议：
  $W# 待机  $C# 检测中  $P# 合格
  $N;类别:置信度;类别:置信度#  不合格(可多个)
类别号：0鼠咬 1毛刺 2缺孔 3短路 4开路 5多余铜
"""
import serial
import time

PORT = "COM3"   # 改成你的CH340 COM号
BAUD = 9600
NAME = ["鼠咬", "毛刺", "缺孔", "短路", "开路", "多余铜"]

def send(ser, frame):
    ser.write(frame.encode("ascii"))
    print("发送:", frame)

def ng_frame(items):
    """items=[(类别号,置信度),...] -> $N;3:93;0:85#"""
    body = "".join(f";{c}:{cf:02d}" for c, cf in items)
    return "$N" + body + "#"

def main():
    try:
        ser = serial.Serial(PORT, BAUD, timeout=1)
    except Exception as e:
        print(f"[错误] 打不开{PORT}：{e}")
        return
    time.sleep(2)

    seq = [
        ("$W#", 3, "待机"),
        ("$C#", 3, "检测中"),
        ("$P#", 3, "合格(无缺陷)"),
        ("$C#", 2, "再检测一张"),
        (ng_frame([(3, 93)]), 4, "不合格-单个: 短路93%"),
        (ng_frame([(3, 93), (0, 85), (1, 70)]), 6, "不合格-多个: 短路/鼠咬/毛刺(轮播)"),
        ("$W#", 3, "回到待机"),
    ]
    for frame, wait, desc in seq:
        print(f"\n[{desc}]")
        send(ser, frame)
        time.sleep(wait)

    print("\n演示结束。")
    ser.close()

if __name__ == "__main__":
    main()
