import cv2
import numpy as np
import matplotlib.pyplot as plt

# 加载 YOLO 模型
net = cv2.dnn.readNet("yolov3.weights", "yolov3.cfg")
layer_names = net.getLayerNames()
output_layers = [layer_names[i - 1] for i in net.getUnconnectedOutLayers()]

# 读取类别名称
with open("coco.names", "r") as f:
    classes = [line.strip() for line in f.readlines()]

# 读取摄像头（若使用图片检测，请替换 0 为文件路径）
cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        print("无法获取摄像头图像")
        break

    height, width, channels = frame.shape
    blob = cv2.dnn.blobFromImage(frame, 0.00392, (416, 416), (0, 0, 0), True, crop=False)
    net.setInput(blob)
    outs = net.forward(output_layers)

    detected_objects = []  # 用于存储检测到的目标类别

    # 解析检测结果
    for out in outs:
        for detection in out:
            scores = detection[5:]
            class_id = np.argmax(scores)  # 获取最高概率的类别 ID
            confidence = scores[class_id]  # 获取对应类别的置信度

            if confidence > 0.5:
                # 计算目标位置
                center_x, center_y, w, h = (detection[:4] * np.array([width, height, width, height])).astype("int")
                x, y = int(center_x - w / 2), int(center_y - h / 2)

                # 获取类别名称
                object_label = classes[class_id]
                detected_objects.append(object_label)

                # 画框 + 标注类别
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.putText(frame, f"{object_label} {confidence:.2f}", (x, y - 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

    # **打印检测结果**
    print(f"检测到的目标: {', '.join(detected_objects)}")

    # **使用 matplotlib 显示（适用于 SSH 远程运行）**
    plt.imshow(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    plt.axis("off")
    plt.show()

    # **保存检测结果到文件**
    cv2.imwrite("detection_result.jpg", frame)
    print("检测完成，已保存为 detection_result.jpg")

    break  # 只检测 1 帧，避免无限循环

cap.release()
