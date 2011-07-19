import os
import sys
import string

import pygame as pg

# TODO:
# - can edit vars defined here through some config editor:
#       takes raw Python code and enters into CONF_DIR/local_conf.py
#       CONF_DIR can't be changed in this way (reject changing it)

# timing
FPS = 10
FRAME = 1. / FPS
MENU_FPS = 30
MENU_FRAME = 1. / MENU_FPS

# paths
DATA_DIR = ''
IMG_DIR = DATA_DIR + 'img' + os.sep
SOUND_DIR = DATA_DIR + 'sound' + os.sep
LEVEL_DIR_MAIN = DATA_DIR + 'lvl' + os.sep
FONT_DIR = DATA_DIR + 'font' + os.sep
CONF_DIR = os.path.expanduser('~') + os.sep + '.pzl' + os.sep
CONF_FILE = CONF_DIR + 'conf'
LEVEL_DIR_CUSTOM = CONF_DIR + 'lvl' + os.sep
LEVEL_DIR_DRAFT = LEVEL_DIR_CUSTOM + 'draft' + os.sep

# CLI
DEBUG = False
SILENT = True
SILENT = SILENT and not DEBUG

# window
RES_F = pg.display.list_modes()[0]
RES_W = (720, 480)
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
KEYS_HOME = (pg.K_HOME,)
KEYS_END = (pg.K_END,)

KEYS_MINIMISE = (pg.K_F10,)
KEYS_FULLSCREEN = (pg.K_F11,)
KEYS_BACK = (pg.K_BACKSPACE, pg.K_ESCAPE)
KEYS_NEXT = (pg.K_SPACE, pg.K_RETURN, pg.K_KP_ENTER)
KEYS_ALTER_LEFT = ((pg.K_LEFT, 0, True),)
KEYS_ALTER_RIGHT = ((pg.K_RIGHT, 0, True),)
KEYS_ALTER_LEFT_BIG = ((pg.K_LEFT, pg.KMOD_ALT, True),)
KEYS_ALTER_RIGHT_BIG = ((pg.K_RIGHT, pg.KMOD_ALT, True),)
KEYS_ALTER_HOME = ((pg.K_LEFT, pg.KMOD_CTRL, True),)
KEYS_ALTER_END = ((pg.K_RIGHT, pg.KMOD_CTRL, True),)
KEYS_RESET = ((pg.K_r, 0, True),)
KEYS_TAB = (pg.K_TAB, pg.K_F8, pg.K_SLASH, pg.K_BACKSLASH)
KEYS_INSERT = KEYS_NEXT + (pg.K_i, pg.K_INSERT)
KEYS_DEL = (pg.K_DELETE, pg.K_d)
KEYS_UNDO = ((pg.K_u, 0, True), (pg.K_z, pg.KMOD_CTRL, True))
KEYS_REDO = ((pg.K_r, pg.KMOD_CTRL, True), (pg.K_y, pg.KMOD_CTRL, True),
             (pg.K_z, (pg.KMOD_CTRL, pg.KMOD_SHIFT), True))

MOVE_INITIAL_DELAY = .2
MOVE_REPEAT_DELAY = .1
MENU_INITIAL_DELAY = .3
MENU_REPEAT_DELAY = .15

# puzzle
FORCE_MOVE = 2
FORCE_ARROW = 2
SOLVE_SPEED = 5 # delay between moves in frames
FF_SPEEDUP = 4
SOLN_DIRS = 'lurd'
SOLN_DIRS_SHOWN = SOLN_DIRS.upper()
MOVE_SOUND = None # SOUND_DIR + 'move.ogg'

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

# selection
SEL_COLOUR = (255, 0, 0)
MIN_SEL_WIDTH = 1
SEL_WIDTH = .05 # proportion of tile size

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
SELECT_STEP = (1, 0.01, 5, 0.05) # small/mid/large/very large; < 1 means
            # fraction of total number of options; >= 1 means absolute value
MIN_SELECT_STEP = (1, 1, 0.01, 5) # as above

# editor
EDITOR_WIDTH = .7 # proportion of screen width (rest for selector)
BLANK_LEVEL = '5 5'
UNDO_LEVELS = 0
LEVEL_NAME_LENGTH = 3

# try to load local conf overrides
path = sys.path
sys.path = [CONF_DIR]
try:
    from local_conf import *
except ImportError:
    pass
sys.path = path

def load_conf ():
    """Load settings dict from file."""
    try:
        with open(CONF_FILE) as f:
            return eval(f.read())
    except:
        return {}

def save_conf (conf):
    """Save given settings dict to file.

All values must have the property that eval(str(value)) == value.

"""
    if not os.path.exists(CONF_DIR):
        os.makedirs(CONF_DIR)
    with open(CONF_FILE, 'w') as f:
        f.write(str(conf))

def get (key, default = None):
    """Get a setting's value.

get(key[, default]) -> value

key: the setting's name.
default: the value to return if the setting has not been saved.  If not given,
         this function tries to return an attribute of this module called
         key.upper(); if this fails, None is returned.

"""
    if default is None:
        try:
            default = globals()[key.upper()]
        except KeyError:
            pass
    return load_conf().get(key, default)

def set (key, value):
    """Save the value of a setting to file.

set(key, value)

key: the setting's name.
value: the value to store.  This must have the property that
       eval(str(value)) == value.

"""
    conf = load_conf()
    conf[key] = value
    save_conf(conf)