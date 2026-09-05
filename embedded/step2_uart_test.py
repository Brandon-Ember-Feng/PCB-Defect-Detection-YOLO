# -*- coding: utf-8 -*-
"""
第2步 v3：电脑端串口回环测试（帧尾#成帧）
前置：pip install pyserial
成功：脚本打印回环成功，开发板LCD第二行完整显示 RX:OK0123456789
"""
import serial
import time

# ====== 改成设备管理器里CH340的实际COM号 ======
PORT = "COM3"
BAUD = 9600
# =============================================

def main():
    try:
        ser = serial.Serial(PORT, BAUD, timeout=1)
    except Exception as e:
        print(f"[错误] 打不开 {PORT}：{e}")
        print("检查：COM号是否正确、开发板是否上电、是否被STC-ISP/串口助手占用")
        return

    time.sleep(2)
    payload = "RX:OK0123456789"
    frame = payload + "#"          # 帧尾#，单片机收到#才整帧显示
    data = frame.encode("ascii")

    print(f"发送 -> {frame}")
    ser.write(data)
    ser.flush()

    time.sleep(0.5)
    echo = ser.read(ser.in_waiting).decode("ascii", errors="replace")
    print(f"收到回显 <- {echo}")

    if payload in echo:
        print("✅ 回环成功：串口双向通信正常，可以进入第3步")
    else:
        print("⚠️ 回环不一致：检查波特率9600、晶振11.0592、USB数据线")

    ser.close()

if __name__ == "__main__":
    main()
