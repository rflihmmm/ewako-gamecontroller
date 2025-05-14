# main.py
import threading
import subprocess
import time

current = 0
lock = threading.Lock()


def update_current():
    global current
    for i in range(1, 21):
        with lock:
            current = i
        print(f"[UPDATE] Current diubah ke {current}")
        time.sleep(2)


def monitor_current():
    current_process = None
    target_file = None

    while True:
        with lock:
            curr = current

        if curr == 5 or curr == 10:
            if curr == 5 and target_file != "lima.py":
                target_file = "lima.py"
                if current_process and current_process.poll() is None:
                    current_process.terminate()
                current_process = subprocess.Popen(["python3", "lima.py"])
                print("[MONITOR] lima.py dijalankan")

            elif curr == 10 and target_file != "sepuluh.py":
                target_file = "sepuluh.py"
                if current_process and current_process.poll() is None:
                    current_process.terminate()
                current_process = subprocess.Popen(["python3", "sepuluh.py"])
                print("[MONITOR] sepuluh.py dijalankan")

            # Tunggu sampai nilai current berubah
            while True:
                time.sleep(0.1)
                with lock:
                    new_curr = current
                if new_curr != curr:
                    if current_process.poll() is None:
                        current_process.terminate()
                        print(f"[MONITOR] {target_file} dihentikan")
                    target_file = None
                    break
        else:
            if current_process and current_process.poll() is None:
                current_process.terminate()
                print("[MONITOR] Proses dihentikan")
            time.sleep(0.1)


if __name__ == "__main__":
    t1 = threading.Thread(target=update_current)
    t2 = threading.Thread(target=monitor_current)

    t1.start()
    t2.start()

    t1.join()
    t2.join()
