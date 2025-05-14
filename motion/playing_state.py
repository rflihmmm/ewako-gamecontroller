import time

counter = 0
while True:
    counter += 1
    if counter > 1000:
        counter = 1
    print(f"Playing State - Counter: {counter}")
    time.sleep(0.5)
