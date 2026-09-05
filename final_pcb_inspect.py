# -*- coding: utf-8 -*-
"""
=====================================================================
 PCB缺陷检测 -> 51单片机LCD1602 上屏  最终上位机（第4步：全链路闭环）
---------------------------------------------------------------------
 流程：每张图  CHECKING($C#) -> YOLO推理 -> PASS($P#) / NG($N;..#)
 51端烧录：step4_ui_display.c （界面状态机）
 协议：
   $W#                 待机 SYSTEM READY
   $C#                 检测中 CHECKING...
   $P#                 合格 PASS
   $N;类别:置信度;..#   不合格，多缺陷聚合，每类取最高置信度(00-99)
   类别ID与模型一致：0鼠咬 1毛刺  2缺孔 3短路 4开路 5多余铜
=====================================================================
"""
import os
import time
import argparse

try:
    import serial                       # pip install pyserial
    from serial.tools import list_ports
except ImportError:
    serial = None

from ultralytics import YOLO            # pip install ultralytics

# ============================ 配置区 ============================
MODEL_PATH = "runs/detect/train-20/weights/best.pt"   # 训练好的权重
SOURCE     = "pcb-defect-dataset/test/images"        # 单张图片 或 图片文件夹
CONF_TH    = 0.25                                    # 模型置信度阈值
IOU_NMS    = 0.45                                    # NMS阈值
SAVE_RESULT= True                                    # 是否保存带框结果图
PORT       = "COM7"                                  # CH340串口号(设备管理器查)
BAUD       = 9600
T_CHECK    = 1.0     # CHECKING界面停留(秒)，模拟检测耗时
T_PASS     = 3.0     # PASS结果停留(秒)
T_NG       = 6.0     # NG结果停留(秒，留时间轮播多个缺陷)
# ===============================================================


class LcdLink:
    """与51单片机的串口连接，打不开也不影响推理（只打印不上屏）"""
    def __init__(self, port, baud):
        self.ser = None
        if serial is None:
            print("[串口] 未安装pyserial，仅打印不上屏。pip install pyserial")
            return
        try:
            self.ser = serial.Serial(port, baud, timeout=1)
            time.sleep(2)
            print(f"[串口] 已连接 {port}@{baud}")
        except Exception as e:
            print(f"[串口] 打开{port}失败：{e}")
            print("可用串口：", [p.device for p in list_ports.comports()])

    def send(self, frame: str):
        """发送一帧并打印"""
        print(f"  [上屏] {frame}")
        if self.ser is not None:
            try:
                self.ser.write(frame.encode("ascii"))
            except Exception as e:
                print(f"  [串口发送失败] {e}")

    def close(self):
        if self.ser is not None:
            self.ser.close()


def build_ng_frame(best: dict) -> str:
    """
    best: {类别id: 最高置信度(0~1)}
    生成 $N;3:93;0:85# ，类别按id排序，置信度转00-99两位整数
    """
    body = ""
    for cls_id in sorted(best.keys()):
        conf = min(99, int(best[cls_id] * 100 + 0.5))   # 两位，封顶99
        body += f";{cls_id}:{conf:02d}"
    return "$N" + body + "#"


def collect_images(source):
    """支持单张图片或文件夹"""
    exts = (".jpg", ".jpeg", ".png", ".bmp")
    if os.path.isfile(source):
        return [source]
    if os.path.isdir(source):
        files = [os.path.join(source, f) for f in sorted(os.listdir(source))
                 if f.lower().endswith(exts)]
        return files
    raise FileNotFoundError(f"找不到图片路径：{source}")


def inspect_one(model, img_path, lcd, names):
    """检测单张：先发CHECKING，再推理，最后按结果发PASS/NG"""
    print("\n" + "=" * 60)
    print("检测图片：", img_path)

    # 1) 检测中
    lcd.send("$C#")
    time.sleep(T_CHECK)

    # 2) YOLO推理
    results = model.predict(img_path, conf=CONF_TH, iou=IOU_NMS,
                            save=SAVE_RESULT, verbose=False)

    # 3) 聚合结果：同一类取最高置信度
    best = {}     # cls_id -> max conf
    total_box = 0
    for r in results:
        for box in r.boxes:
            total_box += 1
            cid = int(box.cls[0])
            cf = float(box.conf[0])
            if cid not in best or cf > best[cid]:
                best[cid] = cf

    # 4) 判定并上屏
    if total_box == 0:
        print("  结果：PASS（未发现缺陷）")
        lcd.send("$P#")
        time.sleep(T_PASS)
    else:
        # 控制台打印明细
        detail = []
        for cid in sorted(best.keys()):
            cname = names.get(cid, str(cid))
            detail.append(f"{cname} {best[cid]*100:.0f}%")
        print(f"  结果：NG，共{total_box}个框，缺陷类别 -> " + " | ".join(detail))
        lcd.send(build_ng_frame(best))
        time.sleep(T_NG)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default=SOURCE, help="图片或文件夹路径")
    ap.add_argument("--port", default=PORT, help="串口号，如 COM3")
    args = ap.parse_args()

    # 加载模型
    print("加载模型：", MODEL_PATH)
    model = YOLO(MODEL_PATH)
    names = model.names
    print("类别映射：", names)

    # 连接单片机
    lcd = LcdLink(args.port, BAUD)
    lcd.send("$W#")   # 上电先回待机

    # 收集图片并逐张检测
    imgs = collect_images(args.source)
    print(f"共 {len(imgs)} 张图片待检测")
    for p in imgs:
        inspect_one(model, p, lcd, names)

    # 全部完成回待机
    lcd.send("$W#")
    lcd.close()
    if SAVE_RESULT:
        print("\n带框结果图保存在 runs/detect/predict 文件夹")
    print("全部检测完成。")


if __name__ == "__main__":
    main()
