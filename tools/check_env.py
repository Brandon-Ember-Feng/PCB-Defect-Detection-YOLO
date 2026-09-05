import torch
import cv2

print("================")
print("PyTorch版本:")
print(torch.__version__)

print("================")
print("CUDA是否可用:")
print(torch.cuda.is_available())


if torch.cuda.is_available():
    print("GPU:")
    print(torch.cuda.get_device_name(0))


print("================")
print("OpenCV版本:")
print(cv2.__version__)