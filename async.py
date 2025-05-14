# main.py
import asyncio
import sys
from multiprocessing import Value, Lock

current = Value('i', 0)
lock = Lock()

async def update_current():
    for i in range(1, 21):
        with lock:
            current.value = i
        print(f"[MAIN] Current updated: {current.value}")
        await asyncio.sleep(2)

async def monitor_current():
    active_process = None
    current_process = None
    
    while True:
        with lock:
            curr = current.value
        
        if curr in (5, 10):
            if curr != active_process:
                # Hentikan proses sebelumnya jika ada
                if current_process:
                    try:
                        current_process.terminate()
                        await current_process.wait()
                        print(f"[MONITOR] Stopped process {active_process}")
                    except ProcessLookupError:
                        pass
                
                # Jalankan proses baru
                file = "lima.py" if curr == 5 else "sepuluh.py"
                current_process = await asyncio.create_subprocess_exec(
                    sys.executable, file,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                active_process = curr
                print(f"[MONITOR] Started {file} (PID: {current_process.pid})")
        else:
            if current_process:
                try:
                    current_process.terminate()
                    await current_process.wait()
                    print(f"[MONITOR] Stopped process {active_process}")
                    active_process = None
                    current_process = None
                except ProcessLookupError:
                    pass
        
        await asyncio.sleep(0.1)

async def main():
    await asyncio.gather(
        update_current(),
        monitor_current()
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[MAIN] Shutting down gracefully...")
