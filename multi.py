# main.py
import asyncio
from multiprocessing import Process, Value
import time


def counter_loop(delay, name):
    counter = 0
    while True:
        counter = (counter % 1000) + 1
        print(f"{name} - Counter: {counter}")
        time.sleep(delay)


def lima():
    counter_loop(0.2, "lima.py")


def sepuluh():
    counter_loop(0.5, "sepuluh.py")


async def update_current(current):
    for i in range(1, 21):
        current.value = i
        print(f"[UPDATE] Current diubah ke {current.value}")
        await asyncio.sleep(2)


async def monitor_current(current):
    processes = {5: None, 10: None}

    while True:
        val = current.value

        if val in processes:
            # Start process jika belum berjalan
            if not processes[val] or not processes[val].is_alive():
                target = lima if val == 5 else sepuluh
                processes[val] = Process(target=target)
                processes[val].start()
                print(f"[MONITOR] Memulai proses {val}")
        else:
            # Hentikan semua proses yang tidak diperlukan
            for key in processes:
                if processes[key] and processes[key].is_alive():
                    processes[key].terminate()
                    print(f"[MONITOR] Menghentikan proses {key}")

        await asyncio.sleep(0.1)


async def main():
    current = Value("i", 0)

    await asyncio.gather(update_current(current), monitor_current(current))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProgram dihentikan")
