#!/usr/bin/env python
# -*- coding:utf-8 -*-

import time
import argparse
import signal
import sys

# Setup signal handling to properly terminate
def signal_handler(sig, frame):
    print("Signal received, exiting...")
    sys.exit(0)

signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

# Parse command line arguments
parser = argparse.ArgumentParser()
parser.add_argument('--team', type=int, required=False, default=1)
parser.add_argument('--player', type=int, required=False, default=1)
parser.add_argument('--state', type=int, required=False, default=0)
parser.add_argument('--first-half', type=str, required=False, default="1")
parser.add_argument('--kick-off-team', type=str, required=False, default="0")
parser.add_argument('--secondary-state', type=str, required=False, default="0")
parser.add_argument('--debug', action='store_true', help='Enable debug output')

args = parser.parse_args()

print(f"Initial State script started for team {args.team}, player {args.player}")
print(f"First half: {args.first_half}, Kick-off team: {args.kick_off_team}, Secondary state: {args.secondary_state}")

counter = 0
try:
    while True:
        counter += 1
        if counter > 1000:
            counter = 1
        print(f"Initial State - Counter: {counter}")
        time.sleep(0.5)
except KeyboardInterrupt:
    print("Interrupted by user, exiting...")
except Exception as e:
    print(f"Error: {e}")
finally:
    print("Initial State script completed")
