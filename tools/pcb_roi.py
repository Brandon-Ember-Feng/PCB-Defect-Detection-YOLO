import cv2
import numpy as np
import os


# ==========================
# 路径
# ==========================

image_path = r"pcb-defect-dataset/train/images/01_missing_hole_02.jpg"  # 改成你的样例图


save_dir = r"output/roi"   # ROI结果输出目录（相对项目根）


os.makedirs(
    save_dir,
    exist_ok=True
)


# ==========================
# 读取图片
# ==========================

img = cv2.imread(image_path)


if img is None:
    print("图片读取失败")
    exit()


print("原图尺寸:", img.shape)



# ==========================
# 灰度
# ==========================

gray = cv2.cvtColor(
    img,
    cv2.COLOR_BGR2GRAY
)



# ==========================
# 高斯滤波
# 去除纹理噪声
# ==========================

blur = cv2.GaussianBlur(
    gray,
    (5,5),
    0
)



# ==========================
# 阈值分割PCB
# ==========================

_, binary = cv2.threshold(
    blur,
    50,
    255,
    cv2.THRESH_BINARY
)



# ==========================
# 查找轮廓
# ==========================

contours,_ = cv2.findContours(
    binary,
    cv2.RETR_EXTERNAL,
    cv2.CHAIN_APPROX_SIMPLE
)



if len(contours)==0:
    print("没有找到PCB")
    exit()



# ==========================
# 最大轮廓
# ==========================

max_contour=max(
    contours,
    key=cv2.contourArea
)



area=cv2.contourArea(
    max_contour
)


print("PCB面积:",area)



# ==========================
# 外接矩形
# ==========================

x,y,w,h=cv2.boundingRect(
    max_contour
)


print(
    "ROI:",
    x,y,w,h
)



# ==========================
# 裁剪PCB
# ==========================

roi=img[
    y:y+h,
    x:x+w
]



# ==========================
# 保存
# ==========================

save_path=os.path.join(
    save_dir,
    "pcb_roi.jpg"
)


cv2.imwrite(
    save_path,
    roi
)


print("ROI保存完成")



# ==========================
# 显示
# ==========================

cv2.imshow(
    "Original",
    img
)


cv2.imshow(
    "Binary",
    binary
)


cv2.imshow(
    "ROI",
    roi
)


cv2.waitKey(0)

cv2.destroyAllWindows()