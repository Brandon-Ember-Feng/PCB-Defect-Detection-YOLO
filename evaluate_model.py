import cv2
import os
import numpy as np
from ultralytics import YOLO
from collections import defaultdict


class ModelEvaluator:
    def __init__(self, model_path, iou_threshold=0.5, conf_threshold=0.25,nms_iou=0.45):
        """
        :param model_path: 模型权重路径
        :param iou_threshold: 判定TP/FP的IoU阈值 (通常0.5)
        :param conf_threshold: 推理置信度阈值
        """
        self.model = YOLO(model_path)
        self.iou_thresh = iou_threshold
        self.conf_thresh = conf_threshold
        self.nms_iou = nms_iou

        # 统计变量
        self.tp = 0  # True Positive
        self.fp = 0  # False Positive
        self.fn = 0  # False Negative
        self.total_gt = 0
        self.total_pred = 0

        # 按类别统计
        self.class_tp = defaultdict(int)
        self.class_fp = defaultdict(int)
        self.class_fn = defaultdict(int)
        self.class_names = {}

    @staticmethod
    def calculate_iou(box1, box2):
        """计算两个框的IoU, 输入格式: [xmin, ymin, xmax, ymax]"""
        x1_min, y1_min, x1_max, y1_max = box1
        x2_min, y2_min, x2_max, y2_max = box2

        inter_xmin = max(x1_min, x2_min)
        inter_ymin = max(y1_min, y2_min)
        inter_xmax = min(x1_max, x2_max)
        inter_ymax = min(y1_max, y2_max)

        inter_area = max(0, inter_xmax - inter_xmin) * max(0, inter_ymax - inter_ymin)
        area1 = (x1_max - x1_min) * (y1_max - y1_min)
        area2 = (x2_max - x2_min) * (y2_max - y2_min)
        union_area = area1 + area2 - inter_area

        return inter_area / union_area if union_area > 0 else 0.0

    def load_gt_labels(self, lbl_path, img_w, img_h):
        """读取YOLO格式标签并转为像素坐标"""
        boxes = []
        if not os.path.exists(lbl_path):
            return boxes

        with open(lbl_path, 'r') as f:
            for line in f.readlines():
                parts = line.strip().split()
                if len(parts) != 5:
                    continue
                cls_id = int(float(parts[0]))
                xc, yc, w, h = map(float, parts[1:])

                # 归一化 -> 像素坐标
                xmin = int((xc - w / 2) * img_w)
                ymin = int((yc - h / 2) * img_h)
                xmax = int((xc + w / 2) * img_w)
                ymax = int((yc + h / 2) * img_h)

                boxes.append({
                    'bbox': [xmin, ymin, xmax, ymax],
                    'class': cls_id,
                    'matched': False
                })
        return boxes

    def evaluate_single_image(self, img_path, lbl_path):
        """评估单张图片"""
        img = cv2.imread(img_path)
        if img is None:
            print(f"Warning: Cannot read {img_path}")
            return

        h, w = img.shape[:2]

        # 1. 加载GT
        gt_boxes = self.load_gt_labels(lbl_path, w, h)
        self.total_gt += len(gt_boxes)

        # 记录类别名（从模型获取）
        if not self.class_names:
            self.class_names = self.model.names

        # 2. 模型预测
        results = self.model.predict(img, verbose=False, conf=self.conf_thresh,iou=self.nms_iou)
        pred_boxes = []
        for r in results:
            for box in r.boxes:
                xyxy = box.xyxy[0].cpu().numpy().tolist()
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                pred_boxes.append({
                    'bbox': xyxy,
                    'class': cls_id,
                    'conf': conf,
                    'matched': False
                })

        self.total_pred += len(pred_boxes)

        # 3. 匹配 TP / FP / FN
        # 按置信度降序排列，优先匹配高置信度预测
        pred_boxes.sort(key=lambda x: x['conf'], reverse=True)

        for pred in pred_boxes:
            best_iou = 0.0
            best_gt_idx = -1

            for gt_idx, gt in enumerate(gt_boxes):
                if gt['matched']:
                    continue
                # 只有同类别才计算IoU
                if pred['class'] != gt['class']:
                    continue

                iou = self.calculate_iou(pred['bbox'], gt['bbox'])
                if iou > best_iou:
                    best_iou = iou
                    best_gt_idx = gt_idx

            if best_iou >= self.iou_thresh and best_gt_idx != -1:
                # TP: 匹配成功
                self.tp += 1
                self.class_tp[pred['class']] += 1
                gt_boxes[best_gt_idx]['matched'] = True
                pred['matched'] = True
            else:
                # FP: 无匹配或IoU不够
                self.fp += 1
                self.class_fp[pred['class']] += 1

        # FN: 未被匹配的GT
        for gt in gt_boxes:
            if not gt['matched']:
                self.fn += 1
                self.class_fn[gt['class']] += 1

    def evaluate_dataset(self, img_dir, lbl_dir):
        """批量评估整个数据集"""
        extensions = ('.jpg', '.jpeg', '.png', '.bmp')
        img_files = [f for f in os.listdir(img_dir) if f.lower().endswith(extensions)]

        if not img_files:
            print("No images found!")
            return

        print(f"Evaluating {len(img_files)} images...")
        print(f"IoU Threshold: {self.iou_thresh} | Conf Threshold: {self.conf_thresh}")
        print("=" * 60)

        for img_file in img_files:
            img_path = os.path.join(img_dir, img_file)
            lbl_file = os.path.splitext(img_file)[0] + '.txt'
            lbl_path = os.path.join(lbl_dir, lbl_file)

            self.evaluate_single_image(img_path, lbl_path)

        self.print_report()

    def print_report(self):
        """打印详细评估报告"""
        precision = self.tp / (self.tp + self.fp) if (self.tp + self.fp) > 0 else 0
        recall = self.tp / (self.tp + self.fn) if (self.tp + self.fn) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

        print("\n" + "=" * 60)
        print("📊 OVERALL METRICS")
        print("=" * 60)
        print(f"  Total GT Boxes:   {self.total_gt}")
        print(f"  Total Predictions:{self.total_pred}")
        print(f"  True Positives:   {self.tp}")
        print(f"  False Positives:  {self.fp}")
        print(f"  False Negatives:  {self.fn}")
        print("-" * 60)
        print(f"  ✅ Precision:     {precision:.4f}  ({self.tp}/{self.tp + self.fp})")
        print(f"  ✅ Recall:        {recall:.4f}  ({self.tp}/{self.tp + self.fn})")
        print(f"  ✅ F1-Score:      {f1:.4f}")
        print("=" * 60)

        # 按类别打印
        all_classes = set(list(self.class_tp.keys()) + list(self.class_fp.keys()) + list(self.class_fn.keys()))

        print("\n📋 PER-CLASS METRICS")
        print("-" * 60)
        print(f"{'Class':<20} {'TP':>5} {'FP':>5} {'FN':>5} {'Prec':>8} {'Recall':>8} {'F1':>8}")
        print("-" * 60)

        for cls_id in sorted(all_classes):
            tp = self.class_tp[cls_id]
            fp = self.class_fp[cls_id]
            fn = self.class_fn[cls_id]

            p = tp / (tp + fp) if (tp + fp) > 0 else 0
            r = tp / (tp + fn) if (tp + fn) > 0 else 0
            f = 2 * p * r / (p + r) if (p + r) > 0 else 0

            name = self.class_names.get(cls_id, f"class_{cls_id}")
            print(f"{name:<20} {tp:>5} {fp:>5} {fn:>5} {p:>8.4f} {r:>8.4f} {f:>8.4f}")

        print("=" * 60)

        # 给出诊断建议
        print("\n💡 DIAGNOSIS:")
        if recall < 0.9:
            print("  ⚠️  Recall偏低 → 存在漏检。建议：降低conf阈值 / 增加难正样本 / 增强数据")
        if precision < 0.9:
            print("  ⚠️  Precision偏低 → 误报较多。建议：提高conf阈值 / 增加硬负样本 / 检查标注质量")
        if recall >= 0.9 and precision >= 0.9:
            print("  🎉 模型表现优秀！可以部署。")
        print()


def main():
    # ================= 配置区域 =================
    MODEL_PATH = "runs/detect/train-20/weights/best.pt"  # <--- 改成你的模型路径
    IMG_DIR = "pcb-defect-dataset/test/images"  # <--- 测试图片文件夹
    LBL_DIR = "pcb-defect-dataset/test/labels"  # <--- 测试标签文件夹

    IOU_THRESHOLD = 0.4  # IoU匹配阈值 (标准值0.5)
    CONF_THRESHOLD = 0.23  # 推理置信度阈值 (与你部署时保持一致)
    # ===========================================

    evaluator = ModelEvaluator(MODEL_PATH, IOU_THRESHOLD, CONF_THRESHOLD)
    evaluator.evaluate_dataset(IMG_DIR, LBL_DIR)


if __name__ == "__main__":
    main()