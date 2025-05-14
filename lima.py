# lima.py
import time

counter = 0
while True:
    counter += 1
    if counter > 1000:
        counter = 1
    print(f"lima.py - Counter: {counter}")
    time.sleep(0.2)