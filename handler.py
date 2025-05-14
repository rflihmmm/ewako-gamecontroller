#!/usr/bin/env python
# -*- coding:utf-8 -*-

from __future__ import unicode_literals, print_function

import os
import time
import signal
import logging
import threading
import subprocess
import argparse
import sys
from enum import Enum

# Import from receiver_2014.py
from receiver_2014 import GameStateReceiver

# Configure logging
logger = logging.getLogger('game_state_handler')
logger.setLevel(logging.DEBUG)

console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
logger.addHandler(console_handler)

# Define game states as Enum for better clarity
class GameStates(Enum):
    STATE_INITIAL = 0
    STATE_READY = 1
    STATE_SET = 2
    STATE_PLAYING = 3
    STATE_FINISHED = 4

# Scripts to run for each game state
# You can customize these paths according to your needs
SCRIPTS = {
    GameStates.STATE_INITIAL.value: "motion/initial_state.py",
    GameStates.STATE_READY.value: "motion/ready_state.py",
    GameStates.STATE_SET.value: "motion/set_state.py",
    GameStates.STATE_PLAYING.value: "motion/playing_state.py",
    GameStates.STATE_FINISHED.value: "motion/finished_state.py"
}

class GameStateHandler(GameStateReceiver):
    """
    Handles different game states by running appropriate scripts
    for each state change received from the GameController.
    """
    
    def __init__(self, team, player, scripts_directory="."):
        """
        Initialize the GameStateHandler.
        
        Args:
            team (int): Team number
            player (int): Player number
            scripts_directory (str): Directory containing state scripts
        """
        super(GameStateHandler, self).__init__(team, player)
        self.scripts_directory = scripts_directory
        self.current_state = None
        self.current_process = None
        self.process_lock = threading.Lock()
        self.state_thread = None
        self.running = True
        
        # Initialize state display
        logger.info("GameStateHandler initialized for team %d, player %d", team, player)
        logger.info("Ready to handle game state changes...")

    def on_new_gamestate(self, state):
        """
        Called when a new game state is received from the GameController.
        
        Args:
            state: The game state received from GameController
        """
        state_value = state.game_state
        state_name = GameStates(state_value).name if state_value in [s.value for s in GameStates] else "UNKNOWN"
        
        logger.info(f"Received game state: {state_value} - {state_name}")
        
        # Skip if state hasn't changed
        if self.current_state == state_value:
            logger.debug(f"State {state_name} unchanged, not restarting script")
            return
            
        # Update state and launch appropriate script in a new thread
        self.current_state = state_value
        
        # Launch in thread to avoid blocking receiver
        if self.state_thread and self.state_thread.is_alive():
            logger.debug("Waiting for previous state thread to complete...")
            self.state_thread.join(1.0)  # Wait max 1 second
            
        self.state_thread = threading.Thread(
            target=self.handle_state_change, 
            args=(state_value, state)
        )
        self.state_thread.daemon = True
        self.state_thread.start()
        
    def handle_state_change(self, state_value, full_state):
        """
        Handles state change by terminating any running script
        and launching the appropriate one for the new state.
        
        Args:
            state_value: The numeric game state value
            full_state: The complete state object with all data
        """
        with self.process_lock:
            # Terminate any running process
            self.terminate_current_process()
            
            # Launch new process if we have a script for this state
            if state_value in SCRIPTS:
                script_path = os.path.join(self.scripts_directory, SCRIPTS[state_value])
                
                # Only try to run the script if it exists
                if os.path.exists(script_path):
                    logger.info(f"Launching script for state {state_value}: {script_path}")
                    
                    # Pass state information as command line arguments
                    cmd = [
                        sys.executable,
                        script_path,
                        "--team", str(self.team),
                        "--player", str(self.player),
                        "--state", str(state_value),
                        "--first-half", str(full_state.first_half),
                        "--kick-off-team", str(full_state.kick_of_team),
                        "--secondary-state", str(full_state.secondary_state)
                    ]
                    
                    # Launch the process
                    try:
                        self.current_process = subprocess.Popen(
                            cmd,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            universal_newlines=True
                        )
                        logger.debug(f"Process started with PID: {self.current_process.pid}")
                        
                        # Optional: Monitor process output in separate thread
                        threading.Thread(
                            target=self.monitor_process_output,
                            args=(self.current_process,),
                            daemon=True
                        ).start()
                        
                    except Exception as e:
                        logger.error(f"Failed to start script {script_path}: {e}")
                else:
                    logger.warning(f"Script {script_path} for state {state_value} not found")
    
    def monitor_process_output(self, process):
        """
        Monitors and logs output from a subprocess.
        
        Args:
            process: The subprocess to monitor
        """
        for line in process.stdout:
            logger.info(f"Script output: {line.strip()}")
        
        for line in process.stderr:
            logger.error(f"Script error: {line.strip()}")
    
    def terminate_current_process(self):
        """Safely terminates the currently running process, if any."""
        if self.current_process:
            try:
                logger.info(f"Terminating previous process (PID: {self.current_process.pid})")
                
                # On Windows, terminate() is the only option
                if os.name == 'nt':
                    self.current_process.terminate()
                else:
                    # On Linux/Unix we can try SIGTERM first, then SIGKILL
                    os.kill(self.current_process.pid, signal.SIGTERM)
                    
                    # Give it a moment to terminate gracefully
                    start_time = time.time()
                    while time.time() - start_time < 1.0:
                        if self.current_process.poll() is not None:
                            break
                        time.sleep(0.1)
                    
                    # If still running, force kill
                    if self.current_process.poll() is None:
                        logger.warning(f"Process didn't terminate, sending SIGKILL to PID: {self.current_process.pid}")
                        os.kill(self.current_process.pid, signal.SIGKILL)
                
                # Wait for process to finish to avoid zombies
                self.current_process.wait(timeout=1.0)
                logger.debug(f"Process terminated with return code: {self.current_process.returncode}")
                
            except subprocess.TimeoutExpired:
                logger.error("Process termination timed out")
            except Exception as e:
                logger.error(f"Error terminating process: {e}")
            finally:
                self.current_process = None
    
    def stop(self):
        """Stop the handler and clean up resources."""
        logger.info("Stopping GameStateHandler")
        self.running = False
        self.terminate_current_process()
        super(GameStateHandler, self).stop()


def create_dummy_scripts():
    """Creates dummy script files for testing if they don't exist."""
    for state, script_name in SCRIPTS.items():
        if not os.path.exists(script_name):
            with open(script_name, 'w') as f:
                f.write(f"""#!/usr/bin/env python
# -*- coding:utf-8 -*-

import sys
import time
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--team', type=int, required=True)
parser.add_argument('--player', type=int, required=True)
parser.add_argument('--state', type=int, required=True)
parser.add_argument('--first-half', type=str, required=True)
parser.add_argument('--kick-off-team', type=str, required=True)
parser.add_argument('--secondary-state', type=str, required=True)

args = parser.parse_args()

print(f"Running state {args.state} script for team {args.team}, player {args.player}")
print(f"First half: {args.first_half}, Kick-off team: {args.kick_off_team}, Secondary state: {args.secondary_state}")

# Simulate some work
for i in range(10):
    print(f"State {args.state} working... {i+1}/10")
    time.sleep(1)
    
print(f"State {args.state} script completed")
""")
            print(f"Created dummy script: {script_name}")
            # Make the script executable on Unix/Linux
            if os.name != 'nt':
                os.chmod(script_name, 0o755)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Game Controller State Handler")
    parser.add_argument('--team', type=int, default=1, help="Team number (default: 1)")
    parser.add_argument('--player', type=int, default=1, help="Player number (default: 1)")
    parser.add_argument('--scripts-dir', type=str, default=".", help="Directory containing state scripts")
    parser.add_argument('--create-dummy-scripts', action='store_true', help="Create dummy scripts for testing")
    
    args = parser.parse_args()
    
    # Create dummy scripts if requested
    if args.create_dummy_scripts:
        create_dummy_scripts()
    
    try:
        handler = GameStateHandler(args.team, args.player, args.scripts_dir)
        
        # Run the receiver in the main thread
        handler.receive_forever()
    except KeyboardInterrupt:
        print("\nKeyboard interrupt received, shutting down...")
    finally:
        if 'handler' in locals():
            handler.stop()
