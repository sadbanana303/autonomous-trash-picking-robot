"""HC-SR04 ultrasonic driver (BOARD pin numbering)."""
import time
import RPi.GPIO as GPIO

SPEED_OF_SOUND_CM_S = 34300
TIMEOUT_S = 0.03

GPIO.setmode(GPIO.BOARD)
GPIO.setwarnings(False)


class UltrasonicSensor:
    def __init__(self, trig, echo, name="sensor"):
        self.trig = trig
        self.echo = echo
        self.name = name
        GPIO.setup(self.trig, GPIO.OUT)
        GPIO.setup(self.echo, GPIO.IN)
        GPIO.output(self.trig, GPIO.LOW)
        time.sleep(0.05)

    def get_distance(self):
        """One reading in cm, or None on timeout."""
        GPIO.output(self.trig, GPIO.HIGH)
        time.sleep(0.00001)
        GPIO.output(self.trig, GPIO.LOW)

        deadline = time.perf_counter() + TIMEOUT_S
        while GPIO.input(self.echo) == 0:
            if time.perf_counter() > deadline:
                return None
        start = time.perf_counter()

        deadline = start + TIMEOUT_S
        while GPIO.input(self.echo) == 1:
            if time.perf_counter() > deadline:
                return None
        end = time.perf_counter()

        return (end - start) * SPEED_OF_SOUND_CM_S / 2

    def get_distance_filtered(self, samples=3):
        """Median of several readings, which rejects single-echo spikes."""
        readings = []
        for _ in range(samples):
            d = self.get_distance()
            if d is not None:
                readings.append(d)
            time.sleep(0.01)
        if not readings:
            return None
        readings.sort()
        return readings[len(readings) // 2]


def cleanup():
    GPIO.cleanup()