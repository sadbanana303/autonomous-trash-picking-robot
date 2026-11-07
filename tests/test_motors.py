import time
import RPi.GPIO as GPIO

# ============================================================
# GPIO SETUP
# ============================================================

GPIO.setmode(GPIO.BOARD)
GPIO.setwarnings(False)

# LEFT BTS7960
LEFT_A = 32
LEFT_B = 33

# RIGHT BTS7960
RIGHT_A = 12
RIGHT_B = 35


# ============================================================
# SETUP GPIO PINS
# ============================================================

for pin in [LEFT_A, LEFT_B, RIGHT_A, RIGHT_B]:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.LOW)


# ============================================================
# PWM SETUP
# ============================================================

PWM_FREQUENCY = 1000

left_pwm_a = GPIO.PWM(LEFT_A, PWM_FREQUENCY)
left_pwm_b = GPIO.PWM(LEFT_B, PWM_FREQUENCY)

right_pwm_a = GPIO.PWM(RIGHT_A, PWM_FREQUENCY)
right_pwm_b = GPIO.PWM(RIGHT_B, PWM_FREQUENCY)

left_pwm_a.start(0)
left_pwm_b.start(0)

right_pwm_a.start(0)
right_pwm_b.start(0)


# ============================================================
# STOP
# ============================================================

def stop():
    """Stop both drive motors."""

    left_pwm_a.ChangeDutyCycle(0)
    left_pwm_b.ChangeDutyCycle(0)

    right_pwm_a.ChangeDutyCycle(0)
    right_pwm_b.ChangeDutyCycle(0)


# ============================================================
# FORWARD
# ============================================================

def forward(speed=30):
    """Move robot physically forward."""

    # LEFT → forward
    left_pwm_a.ChangeDutyCycle(speed)
    left_pwm_b.ChangeDutyCycle(0)

    # RIGHT → forward
    # Right motor is mounted opposite to left motor,
    # so its electrical direction is reversed.
    right_pwm_a.ChangeDutyCycle(0)
    right_pwm_b.ChangeDutyCycle(speed)


# ============================================================
# BACKWARD
# ============================================================

def backward(speed=30):
    """Move robot physically backward."""

    # LEFT → backward
    left_pwm_a.ChangeDutyCycle(0)
    left_pwm_b.ChangeDutyCycle(speed)

    # RIGHT → backward
    right_pwm_a.ChangeDutyCycle(speed)
    right_pwm_b.ChangeDutyCycle(0)


# ============================================================
# TURN LEFT
# ============================================================

def turn_left(speed=30):
    """Rotate robot physically to the left."""

    # LEFT → backward
    left_pwm_a.ChangeDutyCycle(0)
    left_pwm_b.ChangeDutyCycle(speed)

    # RIGHT → forward
    right_pwm_a.ChangeDutyCycle(0)
    right_pwm_b.ChangeDutyCycle(speed)


# ============================================================
# TURN RIGHT
# ============================================================

def turn_right(speed=30):
    """Rotate robot physically to the right."""

    # LEFT → forward
    left_pwm_a.ChangeDutyCycle(speed)
    left_pwm_b.ChangeDutyCycle(0)

    # RIGHT → backward
    right_pwm_a.ChangeDutyCycle(speed)
    right_pwm_b.ChangeDutyCycle(0)


# ============================================================
# MAIN TEST
# ============================================================

try:

    print()
    print("========================================")
    print("       TRASH ROBOT DRIVE TEST")
    print("========================================")
    print()
    print("Motor pins:")
    print("LEFT  : 32 / 33")
    print("RIGHT : 12 / 35")
    print()
    print("Robot should be safely raised")
    print("off the ground for this test.")
    print()
    print("Controls:")
    print("  W = Forward")
    print("  S = Backward")
    print("  A = Left")
    print("  D = Right")
    print("  X = Stop")
    print("  Q = Quit")
    print()

    stop()

    while True:

        command = input("Enter command: ").strip().lower()

        if command == "w":

            print(">>> FORWARD")
            forward(30)

        elif command == "s":

            print(">>> BACKWARD")
            backward(30)

        elif command == "a":

            print(">>> LEFT")
            turn_left(30)

        elif command == "d":

            print(">>> RIGHT")
            turn_right(30)

        elif command == "x":

            print(">>> STOP")
            stop()

        elif command == "q":

            print(">>> QUITTING")
            break

        else:

            print("Unknown command.")
            print("Use W, S, A, D, X or Q.")


except KeyboardInterrupt:

    print()
    print(">>> EMERGENCY STOP")


finally:

    print("Stopping motors...")

    stop()

    left_pwm_a.stop()
    left_pwm_b.stop()

    right_pwm_a.stop()
    right_pwm_b.stop()

    GPIO.cleanup()

    print("GPIO cleaned up.")
