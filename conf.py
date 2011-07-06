import os

import pygame as pg
import string

# timing
FPS = 10
FRAME = 1. / FPS
MENU_FPS = 30
MENU_FRAME = 1. / MENU_FPS

# paths
DATA_DIR = ''
IMG_DIR = DATA_DIR + 'img' + os.sep
LEVEL_DIR_MAIN = DATA_DIR + 'lvl' + os.sep
FONT_DIR = DATA_DIR + 'font' + os.sep
CONF_DIR = os.path.expanduser('~') + os.sep + '.pzl' + os.sep
CONF_FILE = CONF_DIR + 'conf'
LEVEL_DIR_CUSTOM = CONF_DIR + 'lvl' + os.sep

# CLI
DEBUG = False
SILENT = True
SILENT = SILENT and not DEBUG

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
KEYS_ALPHA = range(pg.K_a, pg.K_z + 1)
KEYS_NUM = range(pg.K_0, pg.K_9 + 1)
KEYS_LEFT = (pg.K_LEFT,)
KEYS_UP = (pg.K_UP,)
KEYS_RIGHT = (pg.K_RIGHT,)
KEYS_DOWN = (pg.K_DOWN,)
KEYS_DIR = (pg.K_LEFT, pg.K_UP, pg.K_RIGHT, pg.K_DOWN)

KEYS_MINIMISE = (pg.K_F10,)
KEYS_FULLSCREEN = (pg.K_F11,)
KEYS_BACK = (pg.K_BACKSPACE, pg.K_ESCAPE)
KEYS_NEXT = (pg.K_SPACE, pg.K_RETURN, pg.K_KP_ENTER)
KEYS_RESET = (pg.K_r,)
KEYS_TAB = (pg.K_TAB, pg.K_F8, pg.K_SLASH, pg.K_BACKSLASH)
KEYS_INSERT = KEYS_NEXT + (pg.K_i, pg.K_INSERT)
KEYS_DEL = (pg.K_DELETE, pg.K_d)
KEYS_UNDO = (pg.K_u, pg.K_z)

MOD_SHIFT = pg.KMOD_LSHIFT | pg.KMOD_RSHIFT | pg.KMOD_SHIFT
MOD_CTRL = pg.KMOD_LCTRL| pg.KMOD_RCTRL| pg.KMOD_CTRL
MOD_ALT = pg.KMOD_LALT| pg.KMOD_RALT| pg.KMOD_ALT

MOVE_INITIAL_DELAY = .2
MOVE_REPEAT_DELAY = .1
MENU_INITIAL_DELAY = .3
MENU_REPEAT_DELAY = .15

# puzzle
FORCE_MOVE = 2
FORCE_ARROW = 2

# IDs
MIN_ID = -6
MAX_ID = 4

S_BLANK = -1
S_SLIDE = -2
S_LEFT = -3
S_UP = -4
S_RIGHT = -5
S_DOWN = -6
S_ARROWS = (S_LEFT, S_UP, S_RIGHT, S_DOWN)
DEFAULT_SURFACE = S_BLANK

B_PLAYER = 0
B_IMMOVEABLE = 1
B_STANDARD = 2
B_SLIDE = 3
B_BOUNCE = 4

WALL = 99

# colours
BG = (255, 255, 255)
surface_colours = {
    S_BLANK: (255, 255, 255),
    S_SLIDE: (200, 200, 255)
}
block_colours = {
    B_PLAYER: (200, 0, 0),
    B_IMMOVEABLE: (70, 70, 70),
    B_STANDARD: (150, 150, 150),
    B_SLIDE: (150, 150, 255),
    B_BOUNCE: (100, 255, 100)
}

# messages
MSG_FONT = 'orbitron-black.otf'
MSG_TEXT_COLOUR = (0, 0, 0)
MSG_LINE_HEIGHT = .1 # proportion of smaller screen dimension
MSG_PADDING_TOP = .02 # proportion of smaller screen dimension
MSG_PADDING_BOTTOM = .01 # proportion of smaller screen dimension
MSG_MAX_HEIGHT = .2 # proportion of screen height

# menu
PUZZLE_FONT = 'orbitron-black.otf'
PUZZLE_TEXT_COLOUR = (0, 0, 0)
PUZZLE_TEXT_SELECTED_COLOUR = (255, 0, 0)
PUZZLE_TEXT_SPECIAL_COLOUR = (0, 180, 0)
PUZZLE_TEXT_UPPER = True
PRINTABLE = set(c for c in string.printable if c not in string.whitespace)
PRINTABLE.add(' ')
RAND_B_RATIO = 0.1
RAND_S_RATIO = 0.1
MIN_CHAR_ID = 32
MAX_CHAR_ID = 255
SELECTED_CHAR_ID_OFFSET = 256
SPECIAL_CHAR_ID_OFFSET = 512
LEVEL_SELECT_COLS = 5
NUM_UNCOMPLETED_LEVELS = 5

# editor
BLANK_LEVEL = '5 5'
SEL_COLOUR = (255, 0, 0)
MIN_SEL_WIDTH = 1
SEL_WIDTH = .05 # proportion of tile size
UNDO_LEVELS = 0

def load_conf ():
    try:
        with open(CONF_FILE) as f:
            return eval(f.read())
    except:
        return {}

def save_conf (conf):
    if not os.path.exists(CONF_DIR):
        os.makedirs(CONF_DIR)
    with open(CONF_FILE, 'w') as f:
        f.write(str(conf))

def get (key, default = None):
    return load_conf().get(key, default)

def set (key, value):
    conf = load_conf()
    conf[key] = value
    save_conf(conf)