import os

import pygame as pg

# timing
FPS = 10
FRAME = 1. / FPS

# paths
LEVEL_DIR = 'lvl' + os.sep

# window
RES_W = (640, 480)
RES_F = pg.display.list_modes()[0]
RESIZABLE = True
FULLSCREEN = False
WINDOW_ICON = None
WINDOW_TITLE = 'Puzzle game thing'

# input
KEYS_PAUSE = (pg.K_ESCAPE,)
KEYS_UNPAUSE = (pg.K_SPACE, pg.K_RETURN, pg.K_KP_ENTER)
KEYS_CONTINUE = set(KEYS_UNPAUSE) | set((pg.K_RIGHT, pg.K_DOWN))
KEYS_RESET = (pg.K_r,)
KEYS_MINIMISE = (pg.K_F10,)
KEYS_FULLSCREEN = (pg.K_F11,)
KEYS_LEFT = (pg.K_LEFT,)
KEYS_UP = (pg.K_UP,)
KEYS_RIGHT = (pg.K_RIGHT,)
KEYS_DOWN = (pg.K_DOWN,)

# mechanics
FORCE_MOVE = 2
FORCE_ARROW = 2

MOVE_INITIAL_DELAY = .2
MOVE_REPEAT_DELAY = .1

# IDs
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

# appearance
surface_colours = {
    S_STANDARD: (255, 255, 255),
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