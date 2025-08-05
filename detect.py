import os
import cv2


CUR_DIR = os.path.dirname(__file__)
# Carrega modelo pré-treinado (MobileNet SSD)
net = cv2.dnn.readNetFromCaffe(
    os.path.join(CUR_DIR, "mobilenet_ssd", "MobileNetSSD_deploy.prototxt"),
    os.path.join(CUR_DIR, "mobilenet_ssd", "mobilenet_iter_73000.caffemodel"),
)


# Classe 15 é 'person' no MobileNet SSD
CLASSES = [
    "background",
    "aeroplane",
    "bicycle",
    "bird",
    "boat",
    "bottle",
    "bus",
    "car",
    "cat",
    "chair",
    "cow",
    "diningtable",
    "dog",
    "horse",
    "motorbike",
    "person",
    "pottedplant",
    "sheep",
    "sofa",
    "train",
    "tvmonitor",
]


def detect_person(frame):
    h, w = frame.shape[:2]
    blob = cv2.dnn.blobFromImage(frame, 0.007843, (300, 300), 127.5)
    net.setInput(blob)
    detections = net.forward()

    person_detected = False

    for i in range(detections.shape[2]):
        confidence = detections[0, 0, i, 2]
        if confidence > 0.6:
            idx = int(detections[0, 0, i, 1])
            if CLASSES[idx] == "person":
                person_detected = True
                box = detections[0, 0, i, 3:7] * [w, h, w, h]
                (startX, startY, endX, endY) = box.astype("int")
                cv2.rectangle(frame, (startX, startY), (endX, endY), (0, 255, 0), 2)
                cv2.putText(
                    frame,
                    f"Pessoa: {confidence:.2f}",
                    (startX, startY - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (0, 255, 0),
                    2,
                )

    return frame, person_detected
