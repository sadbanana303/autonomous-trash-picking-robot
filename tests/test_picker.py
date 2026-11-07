import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BOARD)
GPIO.setwarnings(False)

PIN_A = 38
PIN_B = 40

GPIO.setup(PIN_A, GPIO.OUT)
GPIO.setup(PIN_B, GPIO.OUT)

def stop():
    GPIO.output(PIN_A, GPIO.LOW)
    GPIO.output(PIN_B, GPIO.LOW)

try:
    print("Running forward for 10 seconds...")
    GPIO.output(PIN_A, GPIO.HIGH)
    GPIO.output(PIN_B, GPIO.LOW)
    time.sleep(10)

    stop()
    print("Stopped.")

except KeyboardInterrupt:
    print("\nStopped by user")

finally:
    stop()
    GPIO.cleanup()
    print("GPIO cleaned up.")
