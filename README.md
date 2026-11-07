# Autonomous Trash-Picking Robot

![Robot demo](docs/media/demo.gif)

A four-wheeled robot that finds plastic litter with a webcam, drives toward it, and picks it up with a handmade PVC gripper. A Raspberry Pi 4B runs everything on its CPU: YOLOv8n detection, three HC-SR04 ultrasonic sensors, and motor control through three BTS7960 drivers.

Demo video: https://youtu.be/uc-HQsVwEf8

![Robot](docs/media/hero.jpeg)

## How it works

The control loop in `src/main.py` runs once per camera frame.

1. Each webcam frame is resized to 416 px and passed through a YOLOv8n model fine-tuned on the TACO litter dataset, which runs at about 2.4 FPS on the Pi's CPU.
2. Of the detections in four target classes (Other plastic, Plastic bag - wrapper, Plastic container, Unlabeled litter), the robot picks the one with the largest bounding box.
3. If the target sits left or right of a central band (x between 250 and 390 px in a 640 px frame), the robot turns toward it.
4. If the target is centered, the robot drives forward. The left and right ultrasonic sensors steer it away from obstacles closer than 20 cm, and it stops if both sides are blocked.
5. When the center sensor reads 15 cm or less with the target centered, the robot stops and runs the picker motor for 3 seconds.
6. With no target in view, the robot stops.

A background thread polls the three sensors in turn with a 30 ms gap to limit crosstalk and keeps the minimum of the last three readings per sensor. A Flask server streams the annotated camera feed, with bounding boxes, center line and sensor readings, at `http://<pi-ip>:5000/video`.

Pickup is triggered by the center ultrasonic sensor only. The camera-area trigger exists in the code but is disabled (`PICKUP_AREA = 10**9`), because bounding-box area varies too much between object types to serve as a distance estimate.

## Hardware

| Component | Qty | Role |
|:---|:---:|:---|
| Raspberry Pi 4B | 1 | Controller |
| DC motors | 5 | 4 drive, 1 picker |
| BTS7960 motor drivers | 3 | Left side, right side, picker |
| HC-SR04 ultrasonic sensors | 3 | Left, center and right ranging |
| USB webcam | 1 | Detection |
| Acrylic sheet, cardboard, PVC pipe, zip ties | n/a | Chassis and gripper |

Pin map: [docs/wiring.md](docs/wiring.md). Parts and cost: [docs/bill_of_materials.md](docs/bill_of_materials.md). Gripper: [hardware/picker_design_notes.md](hardware/picker_design_notes.md).

## Repository layout

| Path | Contents |
|:---|:---|
| `src/main.py` | Control loop, detection, web stream |
| `src/ultrasonic.py` | HC-SR04 driver |
| `tests/` | Manual bring-up scripts (not a pytest suite) |
| `docs/` | Wiring, parts list, build notes, media |
| `hardware/` | Gripper design notes |

## Setup

On Raspberry Pi OS:

```
git clone https://github.com/sadbanana303/autonomous-trash-picking-robot.git
cd autonomous-trash-picking-robot
python3 -m venv --system-site-packages ~/robot-env
source ~/robot-env/bin/activate
pip install ultralytics flask
```

The trained weights (`best.pt`) are attached to the v1.0 release. Download them and set `MODEL_PATH` at the top of `src/main.py` to the file's location.

The scripts in `tests/` drive the hardware, so run them with the wheels off the ground, one subsystem at a time:

```
python tests/test_motors.py
python tests/test_picker.py
python tests/test_ultrasonic.py
python tests/test_cam_detection.py
python src/main.py
```

Stop `main.py` with Ctrl+C. It stops the motors and releases the GPIO pins on exit.

## Results

### Detection model

YOLOv8n fine-tuned on the TACO dataset (18 classes), validated on 901 images.

| Metric | Value |
|:---|:---:|
| mAP50 | 0.686 |
| mAP50-95 | 0.521 |
| Precision | 0.837 |
| Recall | 0.624 |

Per-class results for the four target classes:

| Class | mAP50 | Note |
|:---|:---:|:---|
| Plastic container | 0.91 | Strongest |
| Plastic bag - wrapper | 0.81 | Strong |
| Other plastic | 0.52 | Weaker |
| Unlabeled litter | 0.39 | Weakest, recall 0.23 |

### On-device performance

| Item | Value |
|:---|:---|
| Hardware | Raspberry Pi 4B, CPU only |
| Input size | 416 px |
| Frame rate | 2.4 FPS |
| Stream | Choppy but usable |

### End-to-end pickup test

| Attempts | Successes | Success rate | Conditions |
|:---:|:---:|:---:|:---|
| 5 | 4 | 80% | Plastic wrappers, plain floor, good light |

![Detection](docs/media/detection_screenshot.png)

## Limitations

- Detection is least reliable for clear or dark plastic and for small, distant items.
- The low frame rate means the robot moves slowly.
- Results come from a small test (5 attempts), not a controlled benchmark.
- The video stream has no authentication, so anyone on the same network can view it.
- The robot only reacts to what is in view. It has no map and does not search.

## Future work

- Run the model on an accelerator or export it to a faster runtime to raise the frame rate.
- Replace the single-sensor pickup trigger with a calibrated distance estimate.
- Add a search behavior for when nothing is in view.

## Authors

Nandana Narendra (https://www.linkedin.com/in/nandana-narendra-115450398/) and Giri Pranesh K (https://www.linkedin.com/in/giri-pranesh-b10448230/)

Released under the MIT License.
