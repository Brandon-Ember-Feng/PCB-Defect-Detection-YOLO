# PCB 缺陷检测系统（YOLOv8 + STC89C52 LCD1602 上屏）

基于 **YOLOv8** 的 PCB 板 6 类缺陷检测上位机，通过串口把检测结果实时下发到 **STC89C52RC 单片机**，在 **LCD1602** 上显示检测状态，并以红绿灯指示合格 / 不合格。是一套「AI 视觉检测 + 嵌入式结果上屏」的完整软硬结合项目。

## 特性
- 检测 6 类 PCB 缺陷：鼠咬、毛刺、缺孔、短路、开路、多余铜
- 自研模型评估脚本：IoU 匹配、TP/FP/FN 统计、分类别精确率/召回率/F1
- 上位机逐张/批量推理，自动按类别聚合最高置信度并组帧下发
- 单片机状态机界面：待机 / 检测中 / 合格 / 不合格，NG 多缺陷自动轮播
- 硬件指示：PASS 绿灯常亮，NG 红灯闪烁报警
- 串口连不上时上位机自动降级为仅打印，不影响推理

## 检测效果（测试集 1068 张 / 1662 个标注框，IoU=0.4，conf=0.23）
| 指标 | 数值 |
|------|------|
| 精确率 Precision | **97.81%** |
| 召回率 Recall | **99.22%** |
| F1-Score | **98.51%** |

各类别召回率均 ≥ 97.85%，其中鼠咬、开路达到 100%。

## 系统架构
```
 PCB图像 ──> PC(Python/YOLOv8推理) ──UART 9600(ASCII帧)──> STC89C52RC
  批量/单张       聚合缺陷+置信度                              ├─ LCD1602 状态/缺陷轮播
                                                             └─ 绿灯(PASS)/红灯闪烁(NG)
```

## 硬件环境（ZY-1 开发板 / STC89C52RC @11.0592MHz）
| 模块 | 引脚 |
|------|------|
| LCD1602 RS / RW / E | P1.0 / P1.1 / P2.5 |
| LCD1602 数据 D0~D7 | P0.0~P0.7 |
| 数码管段选/位选（开机关闭以释放P0） | P2.6 / P2.7 |
| 串口 RXD / TXD（板载 CH340，USB 直连） | P3.0 / P3.1 |
| 绿灯 / 红灯（共阳，输出0点亮） | P1.2 / P1.4 |

## 目录结构
```
├── final_pcb_inspect.py     # 最终上位机：YOLO推理 + 串口上屏（主程序）
├── evaluate_model.py        # 模型评估：IoU/TP/FP/FN、P/R/F1 分类报告
├── configs/pcb.yaml         # 训练配置（类别顺序模板）
├── pretrained/
│   └── pcb_defect_best.pt   # 已训练好的最终权重（约6MB，可直接复现）
├── embedded/                # 单片机代码（Keil C51）
│   ├── step4_ui_display.c   # ★ 最终烧录程序：状态机+NG轮播+红绿灯
│   ├── 视觉检测.hex          # ★ step4 已编译HEX，可直接用STC-ISP烧录
│   ├── step0~step3          # 分阶段验证/调试代码（点灯→LCD→串口→帧解析）
│   └── *_test.py / *_send_frame.py  # 电脑端配套测试脚本
└── tools/                   # 数据工具：改标签ID、数据集/环境/标签检查、ROI提取
```

## 快速开始
### 1. 环境
```bash
pip install ultralytics pyserial opencv-python
```

### 2. 准备数据集
按 YOLO 格式组织 `pcb-defect-dataset/{train,val,test}/{images,labels}`，类别顺序见 `configs/pcb.yaml`（数据集体积较大未入库，需自行准备）。

### 3. 训练
```bash
yolo detect train model=yolov8n.pt data=configs/pcb.yaml epochs=100 imgsz=640 batch=16 device=0
```
> 在已有权重上微调请把学习率降到 lr0≈0.0001、epochs 20~30，避免灾难性遗忘。

### 4. 评估
```bash
python evaluate_model.py
```

### 5. 检测结果上屏
1. Keil 编译 `embedded/step4_ui_display.c`（或直接烧录 `embedded/视觉检测.hex`），STC-ISP 冷启动烧录；
2. 修改 `final_pcb_inspect.py` 顶部 `PORT` 为 CH340 实际串口号；权重路径默认指向 `runs/...`，使用本仓库权重时改为 `pretrained/pcb_defect_best.pt`；
3. 运行：
```bash
python final_pcb_inspect.py                 # 批量（默认遍历 test 目录）
python final_pcb_inspect.py --source xx.jpg # 单张
```

## 类别 ID 映射（标注 / yaml / 模型 / 单片机四处必须一致）
| ID | 英文名 | 中文 | LCD缩写 |
|----|------------------|------|--------|
| 0 | mouse_bite       | 鼠咬 | MBITE |
| 1 | spur             | 毛刺 | SPUR |
| 2 | missing_hole     | 缺孔 | MHOLE |
| 3 | short            | 短路 | SHORT |
| 4 | open_circuit     | 开路 | OPEN |
| 5 | spurious_copper  | 多余铜 | SCOP |

## 串口通信协议（9600, ASCII）
| 帧 | 含义 | LCD 第二行 | 指示灯 |
|----|------|-----------|--------|
| `$W#` | 待机 | SYSTEM READY | 全灭 |
| `$C#` | 检测中 | CHECKING... | 全灭 |
| `$P#` | 合格 | PASS | 绿灯常亮 |
| `$N;3:93;0:85#` | 不合格 | NG SHORT 93%（多项轮播） | 红灯0.5s闪烁 |

NG 帧每项为 `类别:置信度`，置信度为两位整数 00~99，分号分隔，最多 6 项，以 `#` 结尾整帧刷新。

## License
[MIT](LICENSE)
