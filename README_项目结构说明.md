# 基于 YOLOv8 的 PCB 缺陷检测 + STC89C52 LCD1602 上屏系统

> 项目结构说明 / 运行指南 / 硬件协议（整理于 2026-09-05）

## 一、项目简介
- **上位机（PC / Python）**：YOLOv8 检测 PCB 板 6 类缺陷，输出精确率/召回率，并通过串口把检测状态发给单片机。
- **下位机（STC89C52RC / C51）**：LCD1602 显示检测状态，PASS 亮绿灯、NG 红灯闪烁并轮播缺陷类别与置信度。
- **最终测试集成绩（1068 张 / 1662 个标注框）**：精确率 97.81%，召回率 99.22%，F1 值 98.51%。

## 二、目录结构与文件标注
```
Vision_Project/
│
├── final_pcb_inspect.py        ★【最终上位机】YOLO推理 + 串口上屏，批量/单张均可，项目主程序
├── evaluate_model.py           ★【模型评估】自算 IoU/TP/FP/FN、精确率/召回率/F1、分类别报告
├── yolov8n.pt                    预训练权重（训练起点，命令 model=yolov8n.pt 用）
│
├── configs/
│   └── pcb.yaml                  训练配置（已校正类别顺序与数据集路径）
│
├── pcb-defect-dataset/           【数据集，勿删】train 8534 / val 1066 / test 1068
│   ├── train/{images,labels}
│   ├── val/{images,labels}
│   ├── test/{images,labels}      ← 评估与批量演示用的就是 test
│   └── data.yaml                 数据集配置（类别顺序以此为准）
│
├── model_improve/                补充/难例样本（images+labels，用于低lr微调）
│
├── runs/detect/                  训练与推理输出
│   ├── train-20/weights/best.pt  ★ 当前最终使用权重（final 与 evaluate 均指向它）
│   ├── train-10/weights/best.pt    早期最优权重（98.51% F1 那一版，保留对比）
│   └── train-2 ~ train-19/         历次训练迭代记录（保留，可对比）
│
├── weights/                      备用/其他版本权重
│   ├── yolov8s.pt
│   └── yolo26n.pt
│
├── embedded/                     【单片机全部代码，Keil C51 编译烧录】
│   ├── step4_ui_display.c        ★★ 最终51程序：状态机界面 + NG轮播 + 红绿灯（烧这个）
│   ├── step4_ui_test.py            电脑端模拟4状态界面（不接模型也能测51）
│   ├── step3_parse_frame.c        （分阶段验证/调试）定长数据帧解析
│   ├── step3_send_frame.py         （分阶段验证/调试）模拟发送数量帧
│   ├── step2_uart_loopback.c      （分阶段验证/调试）串口回环，整帧接收+volatile
│   ├── step2_uart_test.py          （分阶段验证/调试）电脑端回环测试
│   ├── step1_lcd_test.c           （分阶段验证/调试）LCD1602点亮（纯延时版，已验证）
│   ├── step1b_clear_test.c        （分阶段验证/调试）LCD清屏诊断
│   └── step0_heartbeat.c          （分阶段验证/调试）烧录链路验证：P1灯闪+灭数码管
│
├── tools/                        数据处理/检查工具脚本
│   ├── change_label.py           批量修改YOLO标签类别ID（带_backup备份）
│   ├── check_dataset.py          数据集完整性检查
│   ├── check_labels.py           标签可视化/画框核对
│   ├── check_env.py              PyTorch/OpenCV环境检查
│   └── pcb_roi.py                ROI区域提取工具
│
└── archive/                      【归档】早期探索，已不走该路线，仅留档参考
    └── early_experiments/
        ├── test.py / save.py / detect_grid.py      早期推理、两阶段、网格检测试验
        ├── pcb_roi_extract.py / roi_extract.py     早期ROI提取（两版重复，留档）
        ├── test_result.jpg                         早期测试输出图
        └── opencv/                                 传统OpenCV方案（已被YOLO取代）
```

## 三、完整运行流程
### 1. 训练（需要时）
```
yolo detect train model=yolov8n.pt data=configs/pcb.yaml epochs=100 imgsz=640 batch=16 device=0
```
- 微调已有权重：`model=runs/detect/train-20/weights/best.pt`，并把 `lr0` 降到 0.0001，epochs 20~30，否则会灾难性遗忘。

### 2. 评估模型
```
E:\Python3.11\python.exe evaluate_model.py
```
配置在文件底部 main()：MODEL_PATH / IMG_DIR / LBL_DIR / IoU阈值 / conf阈值。

### 3. 检测结果上屏（最终演示）
1. Keil 编译 `embedded/step4_ui_display.c` → 生成 HEX → STC-ISP 烧录（冷启动），开机显示待机。
2. 修改 `final_pcb_inspect.py` 顶部 `PORT` 为 CH340 实际串口号。
3. 运行：
```
E:\Python3.11\python.exe final_pcb_inspect.py
```
- 单张：`--source 图片路径`；批量：默认遍历 `pcb-defect-dataset/test/images`。
- 串口打不开时不影响推理，只在控制台打印，不会崩溃。

## 四、类别 ID 映射（三处必须一致！）
| ID | 英文名 | 中文 | LCD缩写 |
|----|------------------|--------|--------|
| 0 | mouse_bite       | 鼠咬   | MBITE  |
| 1 | spur             | 毛刺   | SPUR   |
| 2 | missing_hole     | 缺孔   | MHOLE  |
| 3 | short            | 短路   | SHORT  |
| 4 | open_circuit     | 开路   | OPEN   |
| 5 | spurious_copper  | 多余铜 | SCOP   |

> 一致链路：数据集 data.yaml == configs/pcb.yaml == 模型 model.names == 51 的 NAME 表。
> 类别错位是本项目踩过的坑，改类别顺序时四处要同步。

## 五、串口通信协议（9600，ASCII）
| 帧 | 含义 | LCD第二行 | 灯 |
|----|------|-----------|----|
| `$W#` | 待机 | SYSTEM READY | 全灭 |
| `$C#` | 检测中 | CHECKING... | 全灭 |
| `$P#` | 合格 | PASS | 绿灯常亮 |
| `$N;3:93;0:85#` | 不合格 | NG SHORT 93% → 轮播 | 红灯0.5s闪烁 |

- NG帧每项 `类别:置信度`，置信度为两位整数 00~99，最多6项，分号分隔。
- 51收到 `#` 才刷新整帧（逐字节刷新会丢字符）。

## 六、51 硬件引脚（ZY-1开发板，STC89C52RC @11.0592MHz）
| 模块 | 引脚 |
|------|------|
| LCD1602 RS/RW/E | P1.0 / P1.1 / P2.5 |
| LCD1602 数据 D0~D7 | P0.0~P0.7 |
| 数码管段选DU/位选WE | P2.6 / P2.7（开机必须先关闭，释放P0） |
| 串口 RXD/TXD | P3.0 / P3.1（板载CH340，USB直连） |
| 绿灯 | P1.2（板载L2，共阳，输出0点亮） |
| 红灯 | P1.4（板载为黄灯L4；需真红灯可外接LED+1K到J4的P1.4） |

> 注意：板载红灯 L0/L1 的 P1.0/P1.1 已被 LCD 占用，故红绿灯用 P1.2/P1.4。
> 流水灯总开关 J1 跳线帽必须短接，灯才会亮。

## 七、关键踩坑记录（避免重复）
1. **LCD驱动必须纯延时**：本板P0与数码管74HC573复用，忙检测(BF)会读错状态导致死循环。
2. **整帧接收**：串口每收1字节就清屏会丢字符，要攒到帧尾 `#` 再刷新；主循环与中断共享变量加 `volatile`。
3. **类别ID错位**：标注工具顺序、yaml、模型、51缩写表四处对齐。
4. **灾难性遗忘**：用best.pt微调若沿用默认lr0=0.01会把已学特征冲毁，需 lr0≈0.0001。
5. **域偏移**：同源test集高召回、外来图漏检属正常，应补目标场景样本而非暴力重训。
6. **STC-ISP烧录**：点下载后需冷启动（断电再上电）；烧完关闭STC-ISP，否则占用COM口。

## 八、本次整理记录（2026-09-05）
- 归档早期探索脚本到 `archive/early_experiments/`（未删除，可追溯）。
- 数据/检查工具统一到 `tools/`，备用权重统一到 `weights/`。
- 删除：0字节空文件、根目录重复测试脚本、排查用临时裁剪图、__pycache__。
- 删除：传统OpenCV结果图 results/（约821MB）、19个历史 predict 输出（可重新生成）。
- 校正 `configs/pcb.yaml` 的错误类别顺序与失效路径。
- 修正 `final_pcb_inspect.py` 默认图片路径为现存的 test 目录。
- 训练权重 train-* 全部保留；数据集、.venv 未改动。
