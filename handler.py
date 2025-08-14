# handler_with_latency.py
import threading
import subprocess
import time
import socket
from construct import ConstError
from gamestate import GameState
import logging
from collections import deque
import statistics

# Setup logging
logger = logging.getLogger('state_monitor')
logger.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logger.addHandler(console_handler)

# Game Controller configuration
DEFAULT_LISTENING_HOST = '0.0.0.0'
GAME_CONTROLLER_LISTEN_PORT = 3838

# Global variables
current_state = None
lock = threading.Lock()

# Latency tracking
state_change_times = {}  # Track when state changes were received

# Mapping game states to Python files
STATE_FILES = {
    0: "initial_state.py",    # STATE_INITIAL
    1: "ready_state.py",      # STATE_READY
    2: "set_state.py",        # STATE_SET
    3: "playing_state.py",    # STATE_PLAYING
    4: "finished_state.py"    # STATE_FINISHED
}

STATE_NAMES = {
    0: "STATE_INITIAL",
    1: "STATE_READY",
    2: "STATE_SET",
    3: "STATE_PLAYING",
    4: "STATE_FINISHED"
}


class LatencyTracker:
    """Class to track and analyze latency metrics"""
    
    def __init__(self):
        self.measurements = deque(maxlen=1000)
        self.lock = threading.Lock()
    
    def add_measurement(self, latency_ms):
        """Add a latency measurement in milliseconds"""
        with self.lock:
            self.measurements.append(latency_ms)
    
    def get_statistics(self):
        """Get latency statistics"""
        with self.lock:
            if not self.measurements:
                return None
            
            measurements = list(self.measurements)
            return {
                'count': len(measurements),
                'latest': measurements[-1],
                'average': statistics.mean(measurements),
                'median': statistics.median(measurements),
                'min': min(measurements),
                'max': max(measurements),
                'std_dev': statistics.stdev(measurements) if len(measurements) > 1 else 0
            }
    
    def print_statistics(self):
        """Print current latency statistics"""
        stats = self.get_statistics()
        if stats:
            logger.info("=== LATENCY STATISTICS ===")
            logger.info(f"Total measurements: {stats['count']}")
            logger.info(f"Latest: {stats['latest']:.2f} ms")
            logger.info(f"Average: {stats['average']:.2f} ms")
            logger.info(f"Median: {stats['median']:.2f} ms")
            logger.info(f"Min: {stats['min']:.2f} ms")
            logger.info(f"Max: {stats['max']:.2f} ms")
            logger.info(f"Std Dev: {stats['std_dev']:.2f} ms")
            logger.info("========================")


class GameStateListener:
    """Class to listen for game state updates from Game Controller"""
    
    def __init__(self, addr=(DEFAULT_LISTENING_HOST, GAME_CONTROLLER_LISTEN_PORT)):
        self.addr = addr
        self.socket = None
        self.running = True
        self._open_socket()
    
    def _open_socket(self):
        """Create and configure the socket"""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(self.addr)
        self.socket.settimeout(0.5)
    
    def listen_forever(self):
        """Listen for game state updates in a loop"""
        global current_state, state_change_times
        
        while self.running:
            try:
                # Record precise timestamp when data is received
                receive_time = time.time()
                data, peer = self.socket.recvfrom(GameState.sizeof())
                
                # Parse the game state
                parsed_state = GameState.parse(data)
                game_state_enum = parsed_state.game_state
                
                # Convert enum to integer value
                if hasattr(game_state_enum, 'value'):
                    game_state_value = game_state_enum.value
                elif hasattr(game_state_enum, '_value'):
                    game_state_value = game_state_enum._value
                else:
                    # Fallback: try to convert to int directly
                    try:
                        game_state_value = int(game_state_enum)
                    except (ValueError, TypeError):
                        logger.warning(f"Could not convert game state to integer: {game_state_enum}")
                        continue
                
                # Update global state if it changed
                with lock:
                    if current_state != game_state_value:
                        current_state = game_state_value
                        state_change_times[game_state_value] = receive_time
                        state_name = STATE_NAMES.get(game_state_value, f"UNKNOWN({game_state_value})")
                        logger.info(f"Game state changed to: {state_name} ({game_state_value}) at {receive_time:.6f}")
                
            except socket.timeout:
                # Timeout is expected, continue listening
                continue
            except ConstError:
                logger.warning("Parse Error: Probably using an old protocol!")
            except Exception as e:
                logger.error(f"Error receiving game state: {e}")
    
    def stop(self):
        """Stop listening"""
        self.running = False
        if self.socket:
            self.socket.close()


def monitor_game_state():
    """Monitor game state and manage subprocess execution with latency tracking"""
    current_process = None
    current_file = None
    
    while True:
        with lock:
            state = current_state
            receive_time = state_change_times.get(state) if state is not None else None
        
        # Check if we have a valid state and corresponding file
        if state is not None and state in STATE_FILES:
            target_file = STATE_FILES[state]
            
            # If we need to switch to a different file
            if current_file != target_file:
                # Record when we start processing the state change
                process_start_time = time.time()
                
                # Terminate current process if running
                if current_process and current_process.poll() is None:
                    current_process.terminate()
                    current_process.wait()  # Wait for process to actually terminate
                    logger.info(f"[MONITOR] {current_file} terminated")
                
                # Start new process
                try:
                    current_process = subprocess.Popen(["python3", target_file])
                    process_execution_time = time.time()
                    current_file = target_file
                    state_name = STATE_NAMES.get(state, f"UNKNOWN({state})")
                    
                    # Calculate and display latency only once when executing
                    if receive_time:
                        # Total latency from receive to execution
                        total_latency_ms = (process_execution_time - receive_time) * 1000
                        # Processing latency (from start of processing to execution)
                        processing_latency_ms = (process_execution_time - process_start_time) * 1000
                        
                        logger.info(f"[MONITOR] {target_file} started for {state_name} - Latency: {total_latency_ms:.2f}ms (Processing: {processing_latency_ms:.2f}ms)")
                        
                        # Clear the receive time for this state
                        with lock:
                            if state in state_change_times:
                                del state_change_times[state]
                    else:
                        logger.info(f"[MONITOR] {target_file} started for {state_name}")
                        
                except FileNotFoundError:
                    logger.error(f"[MONITOR] File {target_file} not found!")
                    current_file = None
                except Exception as e:
                    logger.error(f"[MONITOR] Error starting {target_file}: {e}")
                    current_file = None
        
        else:
            # No valid state or file, terminate any running process
            if current_process and current_process.poll() is None:
                current_process.terminate()
                current_process.wait()
                logger.info(f"[MONITOR] {current_file} terminated (invalid state)")
                current_file = None
        
        time.sleep(0.1)


def create_sample_state_files():
    """Create sample state files for testing with latency measurement"""
    sample_files = {
        "initial_state.py": '''# initial_state.py
import time
import os

print(f"[{os.getpid()}] INITIAL STATE started at {time.time():.6f}")
counter = 0
while True:
    counter += 1
    print(f"[{os.getpid()}] INITIAL STATE - Counter: {counter}")
    time.sleep(1)
''',
        "ready_state.py": '''# ready_state.py
import time
import os

print(f"[{os.getpid()}] READY STATE started at {time.time():.6f}")
counter = 0
while True:
    counter += 1
    print(f"[{os.getpid()}] READY STATE - Counter: {counter}")
    time.sleep(1)
''',
        "set_state.py": '''# set_state.py
import time
import os

print(f"[{os.getpid()}] SET STATE started at {time.time():.6f}")
counter = 0
while True:
    counter += 1
    print(f"[{os.getpid()}] SET STATE - Counter: {counter}")
    time.sleep(1)
''',
        "playing_state.py": '''# playing_state.py
import time
import os

print(f"[{os.getpid()}] PLAYING STATE started at {time.time():.6f}")
counter = 0
while True:
    counter += 1
    print(f"[{os.getpid()}] PLAYING STATE - Counter: {counter}")
    time.sleep(0.5)
''',
        "finished_state.py": '''# finished_state.py
import time
import os

print(f"[{os.getpid()}] FINISHED STATE started at {time.time():.6f}")
counter = 0
while True:
    counter += 1
    print(f"[{os.getpid()}] FINISHED STATE - Counter: {counter}")
    time.sleep(2)
'''
    }
    
    import os
    for filename, content in sample_files.items():
        if not os.path.exists(filename):
            with open(filename, 'w') as f:
                f.write(content)
            logger.info(f"Created sample file: {filename}")


if __name__ == "__main__":
    # Create sample state files if they don't exist
    create_sample_state_files()
    
    # Create game state listener
    listener = GameStateListener()
    
    # Create and start threads
    listener_thread = threading.Thread(target=listener.listen_forever)
    monitor_thread = threading.Thread(target=monitor_game_state)
    
    listener_thread.daemon = True
    monitor_thread.daemon = True
    
    listener_thread.start()
    monitor_thread.start()
    
    logger.info("State monitor with latency tracking started.")
    logger.info("Listening for game state changes...")
    logger.info("Available states:")
    for state_id, filename in STATE_FILES.items():
        state_name = STATE_NAMES[state_id]
        logger.info(f"  {state_name} ({state_id}) -> {filename}")
    
    try:
        # Keep main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        listener.stop()
        listener_thread.join(timeout=2)
        monitor_thread.join(timeout=2)
