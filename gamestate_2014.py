#!/usr/bin/env python
# -*- coding:utf-8 -*-

from construct import Byte, Struct, Enum, Bytes, Const, Array, Int16ul, Flag, Int16sl

Short = Int16ul

RobotInfo = "robot_info" / Struct(
    # Penalty states from OLD_RoboCupGameControlData.h
    # PENALTY_NONE                        0
    # PENALTY_SPL_BALL_HOLDING            1
    # PENALTY_SPL_PLAYER_PUSHING          2
    # PENALTY_SPL_OBSTRUCTION             3
    # PENALTY_SPL_INACTIVE_PLAYER         4
    # PENALTY_SPL_ILLEGAL_DEFENDER        5
    # PENALTY_SPL_LEAVING_THE_FIELD       6
    # PENALTY_SPL_PLAYING_WITH_HANDS      7
    # PENALTY_SPL_REQUEST_FOR_PICKUP      8
    # PENALTY_SUBSTITUTE                  14
    # PENALTY_MANUAL                      15
    "penalty" / Byte,
    "secs_till_unpenalized" / Byte
)

TeamInfo = "team" / Struct(
    "team_number" / Byte,
    "team_color" / Enum(Byte,
                        BLUE=0,
                        CYAN=0,
                        RED=1,
                        MAGENTA=1
                        ),
    "score" / Byte,
    "penalty_shot" / Byte,  # penalty shot counter
    "single_shots" / Short,  # bits represent penalty shot success
    "coach_message" / Bytes(40),  # Using raw bytes for coach message (size from OLD_SPLCoachMessage.h)
    "players" / Array(11, RobotInfo)  # Support for up to MAX_NUM_PLAYERS (11)
)

GameState = "gamedata" / Struct(
    "header" / Const(b'RGme'),
    "version" / Const(8, Byte),  # Version 8 from OLD_RoboCupGameControlData.h
    "packet_number" / Byte,
    "players_per_team" / Byte,
    "game_state" / Enum(Byte,
                        STATE_INITIAL=0,
                        STATE_READY=1,
                        STATE_SET=2,
                        STATE_PLAYING=3,
                        STATE_FINISHED=4
                        ),
    "first_half" / Byte,
    "kick_of_team" / Byte,
    "secondary_state" / Enum(Byte,
                             STATE2_NORMAL=0,
                             STATE2_PENALTYSHOOT=1,
                             STATE2_OVERTIME=2,
                             STATE2_TIMEOUT=3
                             ),
    "drop_in_team" / Byte,
    "drop_in_time" / Short,
    "seconds_remaining" / Short,
    "secondary_seconds_remaining" / Short,
    "teams" / Array(2, "team" / TeamInfo)
)

GAME_CONTROLLER_RESPONSE_VERSION = 2

ReturnData = Struct(
    "header" / Const(b"RGrt"),
    "version" / Const(2, Byte),
    "team" / Byte,
    "player" / Byte,
    "message" / Byte
)
