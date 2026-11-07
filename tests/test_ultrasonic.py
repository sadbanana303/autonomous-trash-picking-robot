import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import time
from ultrasonic import UltrasonicSensor, cleanup

# Pin assignments (BOARD numbering) -- these are free pins that don't
# conflict with the LEFT/RIGHT/PICKER motor driver pins already in use
# (12, 32, 33, 35, 38, 40).
CENTER_TRIG, CENTER_ECHO = 16, 18
LEFT_TRIG, LEFT_ECHO = 15,7
RIGHT_TRIG, RIGHT_ECHO = 11,13

try:
    center = UltrasonicSensor(CENTER_TRIG, CENTER_ECHO, name="center")
    left = UltrasonicSensor(LEFT_TRIG, LEFT_ECHO, name="left")
    right = UltrasonicSensor(RIGHT_TRIG, RIGHT_ECHO, name="right")

    print("================================")
    print("     ULTRASONIC SENSOR TEST")
    print("================================")
    print()
    print("Reading all 3 sensors. Ctrl+C to stop.")
    print()

    while True:
        d_left = left.get_distance_filtered()
        d_center = center.get_distance_filtered()
        d_right = right.get_distance_filtered()

        def fmt(d):
            return f"{d:5.1f}cm" if d is not None else " no echo"

        print(f"LEFT: {fmt(d_left)}   CENTER: {fmt(d_center)}   RIGHT: {fmt(d_right)}")

        time.sleep(0.2)

except KeyboardInterrupt:
    print("\nStopped.")

finally:
    cleanup()
    print("GPIO cleaned up.")
