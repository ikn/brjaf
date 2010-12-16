import os

import pygame as pg

# timing
FPS = 10
FRAME = 1. / FPS
MENU_FPS = 30
MENU_FRAME = 1. / MENU_FPS

# paths
LEVEL_DIR = 'lvl' + os.sep
FONT_DIR = 'font' + os.sep

# CLI
DEBUG = False
SILENT = True

# window
RES_F = pg.display.list_modes()[0]
RES_W = (640, 480)
MIN_RES_W = (320, 240)
RESIZABLE = True
FULLSCREEN = False
WINDOW_ICON = None
WINDOW_TITLE = 'Puzzle game thing'
MAX_RATIO = 3

# input
KEYS_MINIMISE = (pg.K_F10,)
KEYS_FULLSCREEN = (pg.K_F11,)
KEYS_BACK = (pg.K_BACKSPACE, pg.K_ESCAPE)
KEYS_NEXT = (pg.K_SPACE, pg.K_RETURN, pg.K_KP_ENTER)
KEYS_LEFT = (pg.K_LEFT,)
KEYS_UP = (pg.K_UP,)
KEYS_RIGHT = (pg.K_RIGHT,)
KEYS_DOWN = (pg.K_DOWN,)
KEYS_RESET = (pg.K_r,)

MOVE_INITIAL_DELAY = .2
MOVE_REPEAT_DELAY = .1
MENU_INITIAL_DELAY = .3
MENU_REPEAT_DELAY = .15

# mechanics
FORCE_MOVE = 2
FORCE_ARROW = 2
RAND_B_RATIO = 0.1
RAND_S_RATIO = 0.1

# IDs
MIN_ID = -4
MAX_ID = 4

S_STANDARD = -1
S_SLIDE = -2
S_LEFT = -3
S_UP = -4
S_RIGHT = -5
S_DOWN = -6
S_ARROWS = (S_LEFT, S_UP, S_RIGHT, S_DOWN)

B_PLAYER = 0
B_IMMOVEABLE = 1
B_STANDARD = 2
B_SLIDE = 3
B_BOUNCE = 4

WALL = 99

# puzzle colours
BG = (255, 255, 255)
surface_colours = {
    S_STANDARD: (255, 255, 255),
    S_SLIDE: (200, 200, 255),
    S_LEFT: (255, 200, 200),
    S_UP: (200, 255, 200)
}
block_colours = {
    B_PLAYER: (200, 0, 0),
    B_IMMOVEABLE: (70, 70, 70),
    B_STANDARD: (150, 150, 150),
    B_SLIDE: (150, 150, 255),
    B_BOUNCE: (100, 255, 100)
}

# menu text
PUZZLE_FONT = 'orbitron-black.otf'
PUZZLE_TEXT_COLOUR = (0, 0, 0)
PUZZLE_TEXT_SELECTED_COLOUR = (255, 0, 0)
PUZZLE_TEXT_UPPER = True
MIN_CHAR_ID = 32
MAX_CHAR_ID = 126
SELECTED_CHAR_ID_OFFSET = 128

# puzzle messages
MSG_FONT = 'orbitron-black.otf'
MSG_TEXT_COLOUR = (0, 0, 0)
MSG_LINE_HEIGHT = .1 # proportion of smaller screen dimension
MSG_PADDING_TOP = .02 # proportion of smaller screen dimension
MSG_PADDING_BOTTOM = .01 # proportion of smaller screen dimension
MSG_MAX_HEIGHT = .2 # proportion of screen height