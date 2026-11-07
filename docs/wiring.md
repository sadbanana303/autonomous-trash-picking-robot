# Wiring

![Raspberry Pi pin map](media/wiring_diagram.jpeg)

*Hand-drawn Raspberry Pi 4B pin map. The drawing is labeled as seen facing the robot, so its left and right are mirrored relative to the robot's own sides. The tables below use the robot's own left and right, as in `src/main.py`. The center ultrasonic sensor is not on the drawing and is listed in the sensor table.*

All pin numbers in the tables are BOARD (physical) numbers.

## Motor drivers (BTS7960)

| Driver | Robot's side | RPWM | LPWM |
|:---|:---|:---:|:---:|
| Drive | Left wheels | 32 | 33 |
| Drive | Right wheels | 12 | 35 |
| Picker | n/a | 38 | 40 |

The drive pins run 1 kHz software PWM, at 30% duty for driving and 25% for turning. The picker pins are switched fully on or off. Pi pin 4 (5 V) and pin 6 (GND) supply logic power, shared by all three drivers. [Describe how R_EN and L_EN are wired.] [State the motor battery type and voltage, and how the Pi is powered.]

## Ultrasonic sensors (HC-SR04)

| Sensor | TRIG | ECHO | Trusted range |
|:---|:---:|:---:|:---:|
| Left | 15 | 7 | up to 45 cm |
| Center | 16 | 18 | up to 100 cm |
| Right | 11 | 13 | up to 45 cm |

Sensor power comes from Pi pin 2 (5 V) and pin 25 (GND) through the breadboard. Each ECHO line passes through a voltage divider on the breadboard of [R1] and [R2], since the sensors output 5 V and the Pi's GPIO tolerates 3.3 V. The sensors are polled one at a time with a 30 ms gap so one sensor does not pick up another's pulse.
