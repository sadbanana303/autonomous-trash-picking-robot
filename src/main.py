"""
Autonomous trash-picking robot (Raspberry Pi 4B).

Loop, repeated every frame:
  1. Read a webcam frame and run the YOLO model (best.pt).
  2. Pick the largest detected box in TARGET_CLASSES.
  3. If it is left or right of the center band, turn toward it.
  4. If centered, drive forward, steering away from side obstacles.
  5. If the center sensor reads <= PICKUP_DISTANCE_CM, stop and run the picker.
  6. If no target is visible, stop.

A background thread polls three ultrasonic sensors. A Flask server streams
the annotated camera feed at http://PI_IP:5000/video.
Pin numbers use BOARD numbering. See docs/wiring.md.
"""
import sys
import cv2
import time
import threading
import subprocess
from collections import deque
import RPi.GPIO as GPIO
from ultralytics import YOLO
from flask import Flask, Response
from ultrasonic import UltrasonicSensor


# ============================================================
#                    CONFIGURATION
# ============================================================
MODEL_PATH = "/home/miringa222/best.pt"
CAMERA_INDEX = 0
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480

CONFIDENCE_THRESHOLD = 0.12
YOLO_IMGSZ = 416

TARGET_CLASSES = [
    "Other plastic",
    "Plastic bag - wrapper",
    "Plastic container",
    "Unlabeled litter",
    "Other litter",
    "Paper"
]

CENTER_X = CAMERA_WIDTH // 2
LEFT_THRESHOLD = 220
RIGHT_THRESHOLD = 420

DRIVE_SPEED = 40
TURN_SPEED = 26
SEARCH_SPEED = 22

# Stricter so picker only starts when trash is truly close
PICKUP_AREA = 65000                # higher = wait until closer
BOTTOM_EXIT_Y = int(CAMERA_HEIGHT * 0.92)  # lower line = closer
PICKUP_FORWARD_TIME = 2.0          # keep moving forward while picking
EXIT_WINDOW = 2.8
LOST_GRACE = 1.4

PICKER_TIME = 10.0
AFTER_PICK_DELAY = 0.6


# ============================================================
#                    ULTRASONIC
# ============================================================
CENTER_TRIG, CENTER_ECHO = 16, 18
LEFT_TRIG, LEFT_ECHO = 15, 7
RIGHT_TRIG, RIGHT_ECHO = 11, 13

CENTER_MAX = 100
SIDE_MAX = 55
CENTER_STOP_CM = 20

RIGHT_STOP_CM = 12
RIGHT_CAUTION_CM = 20
LEFT_STOP_CM = 12
LEFT_CAUTION_CM = 20

GAP = 0.04
HISTORY = 6


# ============================================================
#                    GPIO
# ============================================================
GPIO.setmode(GPIO.BOARD)
GPIO.setwarnings(False)

LEFT_A, LEFT_B = 32, 33
RIGHT_A, RIGHT_B = 12, 35
PICKER_A, PICKER_B = 38, 40

for pin in [LEFT_A, LEFT_B, RIGHT_A, RIGHT_B, PICKER_A, PICKER_B]:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.LOW)

PWM_FREQUENCY = 1000
left_pwm_a = GPIO.PWM(LEFT_A, PWM_FREQUENCY)
left_pwm_b = GPIO.PWM(LEFT_B, PWM_FREQUENCY)
right_pwm_a = GPIO.PWM(RIGHT_A, PWM_FREQUENCY)
right_pwm_b = GPIO.PWM(RIGHT_B, PWM_FREQUENCY)

for p in (left_pwm_a, left_pwm_b, right_pwm_a, right_pwm_b):
    p.start(0)


# ============================================================
#                    DRIVE FUNCTIONS
# ============================================================
def _drive(la, lb, ra, rb):
    left_pwm_a.ChangeDutyCycle(la)
    left_pwm_b.ChangeDutyCycle(lb)
    right_pwm_a.ChangeDutyCycle(ra)
    right_pwm_b.ChangeDutyCycle(rb)


def stop_drive():
    _drive(0, 0, 0, 0)


def forward(speed=DRIVE_SPEED):
    _drive(speed, 0, 0, speed)


def reverse(speed=DRIVE_SPEED):
    _drive(0, speed, speed, 0)


def turn_left(speed=TURN_SPEED):
    _drive(0, speed, 0, speed)


def turn_right(speed=TURN_SPEED):
    _drive(speed, 0, speed, 0)


def stop_picker():
    GPIO.output(PICKER_A, GPIO.LOW)
    GPIO.output(PICKER_B, GPIO.LOW)


def start_picker():
    GPIO.output(PICKER_A, GPIO.HIGH)
    GPIO.output(PICKER_B, GPIO.LOW)


if len(sys.argv) > 1 and sys.argv[1] == "picker":
    start_picker()
    time.sleep(5.0)
    stop_picker()
    GPIO.cleanup()
    raise SystemExit


# ============================================================
#                    ULTRASONIC THREAD
# ============================================================
center_sensor = UltrasonicSensor(CENTER_TRIG, CENTER_ECHO, name="center")
left_sensor   = UltrasonicSensor(LEFT_TRIG, LEFT_ECHO, name="left")
right_sensor  = UltrasonicSensor(RIGHT_TRIG, RIGHT_ECHO, name="right")

distances = {"left": None, "center": None, "right": None}
dist_lock = threading.Lock()
stop_event = threading.Event()

last_avoid_time = 0.0
AVOID_COOLDOWN = 1.0


def sensor_loop():
    sensors = (
        ("left", left_sensor, SIDE_MAX),
        ("center", center_sensor, CENTER_MAX),
        ("right", right_sensor, SIDE_MAX),
    )
    hist = {key: deque(maxlen=HISTORY) for key, _, _ in sensors}

    while not stop_event.is_set():
        for key, sensor, max_range in sensors:
            try:
                d = sensor.get_distance_filtered()
            except Exception:
                d = None
            hist[key].append(d if (d is not None and 2 < d < max_range) else None)

            valid = [x for x in hist[key] if x is not None]
            with dist_lock:
                if len(valid) >= 4:
                    distances[key] = sorted(valid)[len(valid) // 2]
                else:
                    distances[key] = None
            time.sleep(GAP)


def get_distances():
    with dist_lock:
        return distances["left"], distances["center"], distances["right"]


def fmt(d):
    return f"{d:.0f}cm" if d is not None else "clear"


sensor_thread = threading.Thread(target=sensor_loop, daemon=True)
sensor_thread.start()


# ============================================================
#                    YOLO + CAMERA
# ============================================================
print("\n=== TRASH ROBOT STARTING ===")
print("Loading YOLO model...")
model = YOLO(MODEL_PATH)
print("Model classes:", model.names)

cap = cv2.VideoCapture(CAMERA_INDEX)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

if not cap.isOpened():
    print("ERROR: Camera could not be opened.")
    stop_event.set()
    GPIO.cleanup()
    raise SystemExit
print("Camera opened successfully.")


# ============================================================
#                    FLASK STREAM
# ============================================================
app = Flask(__name__)
frame_to_stream = None
frame_lock = threading.Lock()


def generate_frames():
    while True:
        with frame_lock:
            frame = None if frame_to_stream is None else frame_to_stream.copy()
        if frame is not None:
            ok, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
            if ok:
                yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n"
                       + buf.tobytes() + b"\r\n")
        time.sleep(0.05)


@app.route("/video")
def video():
    return Response(generate_frames(),
                    mimetype="multipart/x-mixed-replace; boundary=frame")


def start_flask():
    try:
        ip = subprocess.check_output(["hostname", "-I"]).decode().strip().split()[0]
        print(f"\n>>> Camera stream: http://{ip}:5000/video <<<\n")
        app.run(host="0.0.0.0", port=5000, threaded=True, debug=False, use_reloader=False)
    except Exception as e:
        print(f"Flask error: {e}")


threading.Thread(target=start_flask, daemon=True).start()
time.sleep(1.5)


# ============================================================
#                    VISION THREAD
# ============================================================
det_lock = threading.Lock()
det = {"target": None, "time": 0.0}


def vision_loop():
    global frame_to_stream
    while not stop_event.is_set():
        ret, frame = cap.read()
        if not ret:
            time.sleep(0.04)
            continue

        result = model(frame, conf=CONFIDENCE_THRESHOLD,
                       imgsz=YOLO_IMGSZ, verbose=False)[0]

        target = None
        if result.boxes is not None:
            for box in result.boxes:
                name = model.names[int(box.cls[0])]
                conf = float(box.conf[0])
                if name not in TARGET_CLASSES or conf < CONFIDENCE_THRESHOLD:
                    continue
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                area = (x2 - x1) * (y2 - y1)
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(frame, f"{name} {conf:.2f} a={area}", (x1, max(20, y1 - 10)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                if target is None or area > target["area"]:
                    target = {
                        "name": name,
                        "conf": conf,
                        "area": area,
                        "cx": (x1 + x2) // 2,
                        "y2": y2
                    }

        if target is not None:
            with det_lock:
                det["target"] = target
                det["time"] = time.time()

        cv2.line(frame, (CENTER_X, 0), (CENTER_X, CAMERA_HEIGHT), (255, 0, 0), 1)
        cv2.line(frame, (0, BOTTOM_EXIT_Y), (CAMERA_WIDTH, BOTTOM_EXIT_Y), (0, 0, 255), 2)

        dl, dc, dr = get_distances()
        cv2.putText(frame, f"L:{fmt(dl)} C:{fmt(dc)} R:{fmt(dr)}", (10, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

        with frame_lock:
            frame_to_stream = frame


threading.Thread(target=vision_loop, daemon=True).start()


# ============================================================
#                    HELPERS
# ============================================================
last_msg = ""
def say(msg):
    global last_msg
    if msg != last_msg:
        print(msg)
        last_msg = msg


def pickup_while_moving():
    """Drive forward while the picker is running for 5 seconds."""
    say("Trash close → FORWARD + PICKER (5s)")
    start_picker()
    end = time.time() + PICKUP_FORWARD_TIME
    while time.time() < end:
        dl, dc, dr = get_distances()
        if (dc is not None and dc <= CENTER_STOP_CM) or \
           (dl is not None and dl <= LEFT_STOP_CM) or \
           (dr is not None and dr <= RIGHT_STOP_CM):
            break
        forward(DRIVE_SPEED - 6)
        time.sleep(0.05)

    # Continue picker for the full 5 seconds even if we stopped early
    remaining = PICKER_TIME - (time.time() - (end - PICKUP_FORWARD_TIME))
    if remaining > 0.3:
        time.sleep(remaining)

    stop_picker()
    stop_drive()
    reverse(20)
    time.sleep(0.35)
    stop_drive()
    time.sleep(AFTER_PICK_DELAY)
    with det_lock:
        det["target"] = None
    say("Pickup finished")


def avoid_obstacle(d_left, d_center, d_right):
    global last_avoid_time
    if time.time() - last_avoid_time < AVOID_COOLDOWN:
        return False

    left_blocked   = d_left  is not None and d_left  <= LEFT_STOP_CM
    right_blocked  = d_right is not None and d_right <= RIGHT_STOP_CM
    center_blocked = d_center is not None and d_center <= CENTER_STOP_CM
    left_close     = d_left  is not None and d_left  <= LEFT_CAUTION_CM
    right_close    = d_right is not None and d_right <= RIGHT_CAUTION_CM

    if not (center_blocked or left_blocked or right_blocked or left_close or right_close):
        return False

    last_avoid_time = time.time()

    if left_blocked and right_blocked:
        say("Both sides blocked → reverse + turn")
        reverse(DRIVE_SPEED)
        time.sleep(0.40)
        l = d_left  if d_left  is not None else 999
        r = d_right if d_right is not None else 999
        if l >= r:
            turn_left(TURN_SPEED)
        else:
            turn_right(TURN_SPEED)
        time.sleep(0.45)
        stop_drive()
        return True

    if center_blocked:
        l = d_left  if d_left  is not None else 999
        r = d_right if d_right is not None else 999
        reverse(DRIVE_SPEED)
        time.sleep(0.28)
        if l >= r and not left_blocked:
            say(f"Center {fmt(d_center)} → LEFT")
            turn_left(TURN_SPEED)
        elif r > l and not right_blocked:
            say(f"Center {fmt(d_center)} → RIGHT")
            turn_right(TURN_SPEED)
        else:
            stop_drive()
        time.sleep(0.35)
        stop_drive()
        return True

    if left_blocked or left_close:
        say(f"Left {fmt(d_left)} → reverse + RIGHT")
        reverse(DRIVE_SPEED)
        time.sleep(0.20)
        turn_right(TURN_SPEED)
        time.sleep(0.38)
        stop_drive()
        return True

    if right_blocked or right_close:
        say(f"Right {fmt(d_right)} → reverse + LEFT")
        reverse(DRIVE_SPEED)
        time.sleep(0.20)
        turn_left(TURN_SPEED)
        time.sleep(0.38)
        stop_drive()
        return True

    return False


# ============================================================
#                    MAIN LOOP
# ============================================================
print("\n=== AUTONOMOUS MODE READY ===\n")

try:
    while True:
        now = time.time()
        d_left, d_center, d_right = get_distances()

        with det_lock:
            target = det["target"]
            age = now - det["time"]

        seen = target is not None and age <= LOST_GRACE
        centered = seen and LEFT_THRESHOLD <= target["cx"] <= RIGHT_THRESHOLD

        # 1. Obstacle avoidance first
        if avoid_obstacle(d_left, d_center, d_right):
            time.sleep(0.05)
            continue

        # 2. Target visible and close enough → forward + picker
        if seen:
            cx = target["cx"]
            y2 = target["y2"]
            area = target["area"]

            # Only start when trash is truly close
            if area >= PICKUP_AREA and y2 >= BOTTOM_EXIT_Y and centered:
                pickup_while_moving()
                continue

            # Normal steering
            if cx < LEFT_THRESHOLD:
                say("Trash LEFT → turning left")
                turn_left(TURN_SPEED)
            elif cx > RIGHT_THRESHOLD:
                say("Trash RIGHT → turning right")
                turn_right(TURN_SPEED)
            else:
                say(f"Trash CENTER (area={area}) → forward")
                forward(DRIVE_SPEED)

        # 3. Just exited the bottom of the frame
        elif (target is not None and age <= EXIT_WINDOW
              and target["y2"] >= BOTTOM_EXIT_Y
              and LEFT_THRESHOLD - 70 <= target["cx"] <= RIGHT_THRESHOLD + 70):
            pickup_while_moving()

        # 4. Searching
        else:
            say("Searching → forward")
            forward(SEARCH_SPEED)

        time.sleep(0.04)

except KeyboardInterrupt:
    print("\n=== EMERGENCY STOP ===")

finally:
    print("Stopping robot...")
    stop_event.set()
    stop_drive()
    stop_picker()
    sensor_thread.join(timeout=1.5)
    for p in (left_pwm_a, left_pwm_b, right_pwm_a, right_pwm_b):
        p.stop()
    time.sleep(0.2)
    cap.release()
    GPIO.cleanup()
    print("Robot stopped safely.")