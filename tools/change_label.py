import os
import shutil


def replace_label_class_ids(label_dir, replace_map, backup=True, line_count=None, file_count=None):
    """
    批量替换YOLO格式标签文件中的类别ID
    :param label_dir: 标签文件夹路径 (里面全是.txt文件)
    :param replace_map: 替换映射字典 {旧ID: 新ID}，例如 {0:1, 2:0}
    :param backup: 是否备份原文件，默认True
    """
    if not os.path.exists(label_dir):
        print(f"错误：文件夹不存在 → {label_dir}")
        return

    # 1. 备份原文件（安全第一）
    #if backup:
        backup_dir = label_dir + "_backup"
        if os.path.exists(backup_dir):
            shutil.rmtree(backup_dir)
        shutil.copytree(label_dir, backup_dir)
        print(f"✅ 原文件已备份到 → {backup_dir}")

    file_count = 0
    line_count = 0

    # 2. 遍历所有txt标签文件
    for filename in os.listdir(label_dir):
        if not filename.lower().endswith('.txt'):
            continue

        file_path = os.path.join(label_dir, filename)
        new_lines = []
        has_change = False

        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f.readlines():
                line = line.strip()
                if not line:
                    new_lines.append('')
                    continue

                parts = line.split()
                if len(parts) < 5:
                    new_lines.append(line)
                    continue

                old_cls = parts[0]
                # 尝试转成数字匹配
                try:
                    old_id = int(float(old_cls))
                except ValueError:
                    new_lines.append(line)
                    continue

                # 匹配替换规则
                if old_id in replace_map:
                    new_id = replace_map[old_id]
                    parts[0] = str(new_id)
                    new_lines.append(' '.join(parts))
                    has_change = True
                    line_count += 1
                else:
                    new_lines.append(line)

        # 3. 写回文件（只有修改过才重写）
        if has_change:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(new_lines) + '\n')
            file_count += 1
            print(f"  已修改: {filename}")

    print("\n" + "=" * 50)
    print(f"处理完成！共修改 {file_count} 个文件，替换 {line_count} 个标签ID")
    if backup:
        print(f"如需恢复，直接删除原文件夹，把 {backup_dir} 改回原名即可")


# ====================== 配置区域（改这里就行） ======================
if __name__ == "__main__":
    # 你的标签文件夹路径
    LABEL_DIR = ("model_improve/labels/val")

    # 替换规则：{旧类别ID: 新类别ID}
    # 比如你要把 类别2 改成 类别1，就写 {2: 1}
    # 多个替换一起写：{0:1, 1:2, 2:0}
    REPLACE_MAP = {
        0: 2,
        1:0,2:4,4:5,5:1# 把原来ID=2的标签，改成ID=1
        # 继续加你的替换规则...
    }

    replace_label_class_ids(LABEL_DIR, REPLACE_MAP, backup=True)
# ===================================================================
