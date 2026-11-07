"""
Camera detection test (manual bring-up script, run on the Pi).

Uses the same model and target classes as src/main.py. Runs for 20 seconds,
prints each detected target with its confidence and horizontal offset
(-1 = far left, +1 = far right), and saves up to 5 annotated frames to
tests/output/.

Correct behavior: holding up a plastic item prints detection lines and
creates detect_0.jpg, detect_1.jpg, etc. The final line reports FPS.
"""
import os
import time
import cv2
from ultralytics import YOLO

MODEL_PATH = "/home/miringa222/best.pt"
CAMERA_INDEX = 0
W, H = 640, 480
CONF = 0.35
TARGET_CLASSES = ["Other plastic", "Plastic bag - wrapper",
                  "Plastic container", "Unlabeled litter"]

out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
os.makedirs(out_dir, exist_ok=True)

model = YOLO(MODEL_PATH)
cap = cv2.VideoCapture(CAMERA_INDEX)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, W)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, H)
if not cap.isOpened():
    raise SystemExit("Camera not found. Check the USB cable or CAMERA_INDEX.")
for _ in range(10):
    cap.read()

frames = saved = 0
start = time.time()
try:
    while time.time() - start < 20:
        ok, frame = cap.read()
        if not ok:
            print("Frame read failed")
            break
        frames += 1
        result = model(frame, conf=CONF, verbose=False)[0]
        hit = False
        for box in result.boxes:
            name = model.names[int(box.cls[0])]
            if name not in TARGET_CLASSES:
                continue
            x1, _, x2, _ = box.xyxy[0].tolist()
            offset = ((x1 + x2) / 2 - W / 2) / (W / 2)
            print(f"{name} conf={float(box.conf[0]):.2f} offset={offset:+.2f}")
            hit = True
        if hit and saved < 5:
            cv2.imwrite(os.path.join(out_dir, f"detect_{saved}.jpg"), result.plot())
            saved += 1
finally:
    cap.release()

dt = time.time() - start
print(f"{frames} frames in {dt:.1f}s = {frames / dt:.1f} FPS, {saved} images saved")