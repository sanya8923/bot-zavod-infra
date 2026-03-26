import signal
import time

running = True


def handle_signal(signum, frame):
    global running
    running = False


signal.signal(signal.SIGTERM, handle_signal)
signal.signal(signal.SIGINT, handle_signal)

print("Python runner is up!")

while running:
    time.sleep(60)
