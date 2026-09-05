import os


dataset_path = r"pcb-defect-dataset"   # 数据集路径（相对项目根，按实际修改）


image_train = os.path.join(
    dataset_path,
    "images/train"
)

label_train = os.path.join(
    dataset_path,
    "labels/train"
)


images = os.listdir(image_train)

labels = os.listdir(label_train)


print("训练图片数量:", len(images))

print("训练标签数量:", len(labels))


# 检查缺失标签

missing=[]


for img in images:

    name=os.path.splitext(img)[0]

    txt=name+".txt"

    if txt not in labels:
        missing.append(img)



print("================")

print("缺失标签图片:")

print(missing)



# 类别统计

classes={}


for txt in labels:

    file=os.path.join(
        label_train,
        txt
    )

    with open(file,"r") as f:

        lines=f.readlines()


    for line in lines:

        cls=line.split()[0]

        classes[cls]=classes.get(cls,0)+1



print("================")

print("类别数量:")

print(classes)