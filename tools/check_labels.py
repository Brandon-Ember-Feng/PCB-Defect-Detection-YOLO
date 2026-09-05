import cv2
import os


# =========================
# 路径配置
# =========================

image_dir = "test_images/images"
label_dir = "test_images/labels"

save_dir = "results/label_check_test"


# 创建保存目录
os.makedirs(save_dir, exist_ok=True)


# =========================
# PCB缺陷类别
# 根据你的数据集修改
# =========================

classes = [
    "missing_hole",
    "mouse_bite",
    "open_circuit",
    "short",
    "spurious_copper",
    "spur"
]


# =========================
# 获取图片
# =========================

image_files = os.listdir(image_dir)


for image_file in image_files:

    if not image_file.endswith((".jpg",".png",".jpeg")):
        continue


    # 图片路径
    image_path = os.path.join(
        image_dir,
        image_file
    )


    # 标签路径
    label_file = os.path.splitext(image_file)[0]+".txt"

    label_path = os.path.join(
        label_dir,
        label_file
    )


    # 读取图片
    img = cv2.imread(image_path)


    if img is None:
        continue


    h,w,_ = img.shape


    # =========================
    # 读取YOLO标签
    # =========================

    if os.path.exists(label_path):

        with open(label_path,"r") as f:

            labels=f.readlines()


        for label in labels:


            data = label.strip().split()


            if len(data)!=5:
                continue


            cls = int(data[0])


            x_center = float(data[1])
            y_center = float(data[2])
            bw = float(data[3])
            bh = float(data[4])


            # YOLO归一化坐标
            x1 = int(
                (x_center-bw/2)*w
            )

            y1 = int(
                (y_center-bh/2)*h
            )

            x2 = int(
                (x_center+bw/2)*w
            )

            y2 = int(
                (y_center+bh/2)*h
            )


            # 防止越界
            x1=max(0,x1)
            y1=max(0,y1)
            x2=min(w,x2)
            y2=min(h,y2)


            # 绘制框
            cv2.rectangle(
                img,
                (x1,y1),
                (x2,y2),
                (0,255,0),
                2
            )


            # 类别名称
            if cls < len(classes):
                name = classes[cls]
            else:
                name="unknown"


            # 添加文字
            cv2.putText(
                img,
                name,
                (x1,y1-5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0,255,0),
                2
            )


    # 保存结果

    save_path=os.path.join(
        save_dir,
        image_file
    )


    cv2.imwrite(
        save_path,
        img
    )


print("标签可视化完成！")