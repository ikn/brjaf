"""Brain Requirement Just A Formality.  Copyright 2011 by J.

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

"""

# TODO: more keyboard layouts: https://en.wikipedia.org/wiki/Keyboard_layout

import os
import sys
import string

import pygame as pg

# need to take care to get unicode path
if os.name == 'nt':
    try:
        import ctypes
        n = ctypes.windll.kernel32.GetEnvironmentVariableW(u'APPDATA', None, 0)
        if n == 0:
            raise ValueError()
    except:
        # fallback (doesn't get unicode string)
        CONF_DIR = os.environ[u'APPDATA']
    else:
        buf = ctypes.create_unicode_buffer(u'\0' * n)
        ctypes.windll.kernel32.GetEnvironmentVariableW(u'APPDATA', buf, n)
        CONF_DIR = buf.value
else:
    CONF_DIR = os.path.expanduser(u'~')
CONF_DIR += os.sep + ('' if os.name == 'nt' else '.') + 'brjaf' + os.sep
CONF_FILE = CONF_DIR + 'conf'

# read local conf file into dict
_local = {}
try:
    with open(CONF_FILE) as f:
        lines = f.readlines()
except IOError:
    pass
else:
    for line in lines:
        if line.startswith('#'):
            # comment
            continue
        # split line into key/value by first =
        eq = line.find('=')
        if eq == -1:
            continue
        k = line[:eq].strip()
        v = line[eq + 1:].strip()
        _local[k] = v

def save_conf ():
    """Save current changed settings to file."""
    if not os.path.exists(CONF_DIR):
        os.makedirs(CONF_DIR)
    with open(CONF_FILE, 'w') as f:
        s = '\n'.join('{0} = {1}'.format(k, v) for k, v in _local.iteritems())
        f.write(s)

def get (key, default = None):
    """Get a setting's value.

get(key, default = None) -> value

key: the setting's name; case-insensitive.
default: the value to return if the setting has not been saved.

"""
    # look in this module first, then _local, then return default
    try:
        return globals()[key.upper()]
    except KeyError:
        try:
            return eval(_local[key.upper()])
        except KeyError:
            return default


# timing
FPS = get('fps', 10)
FRAME = get('frame', 1. / FPS)
MENU_FPS = get('menu_fps', 30)
MENU_FRAME = get('menu_frame', 1. / MENU_FPS)

# paths
DATA_DIR = get('data_dir', '')
IMG_DIR = get('img_dir', DATA_DIR + 'img' + os.sep)
SOUND_DIR = get('sound_dir', DATA_DIR + 'sound' + os.sep)
MUSIC_DIR = get('music_dir', DATA_DIR + 'music' + os.sep)
LEVEL_DIR_MAIN = get('level_dir_main', DATA_DIR + 'lvl' + os.sep)
FONT_DIR = get('font_dir', DATA_DIR + 'font' + os.sep)
LEVEL_DIR_CUSTOM = get('level_dir_custom', CONF_DIR + 'lvl' + os.sep)
LEVEL_DIR_DRAFT = get('level_dir_draft', LEVEL_DIR_CUSTOM + 'draft' + os.sep)

# CLI
DEBUG = get('debug', False)
SILENT = get('silent', True and not DEBUG)

# window
WINDOW_ICON = get('window_icon', 'icon.png')
WINDOW_TITLE = get('window_title', 'Brain requirement just a formality')
MOUSE_VISIBLE = get('mouse_visible', True)
RESIZABLE = get('resizable', True)
FULLSCREEN = get('fullscreen', False)
RES_F = get('res_f', pg.display.list_modes()[0])
RES_W = get('res_w', (720, 480))
FLAGS = get('flags', 0)
MIN_RES_W = get('min_res_w', (320, 240))
ASPECT_RATIO = get('aspect_ratio', None)
MAX_RATIO = get('max_ratio', (3, 2))

# input
KEYS_LEFT = get('keys_left', (pg.K_LEFT,))
KEYS_UP = get('keys_up', (pg.K_UP,))
KEYS_RIGHT = get('keys_right', (pg.K_RIGHT,))
KEYS_DOWN = get('keys_down', (pg.K_DOWN,))
KEYS_HOME = get('keys_home', (pg.K_HOME,))
KEYS_END = get('keys_end', (pg.K_END,))
KEYS_PAGE_UP = get('keys_page_up', (pg.K_PAGEUP,))
KEYS_PAGE_DOWN = get('keys_page_down', (pg.K_PAGEDOWN,))
KEYS_SOLN_NEXT = get('keys_soln_next', KEYS_RIGHT)
# movement keys: l/u/r/d/ul/ur/dr/dl
KEYS_MOVE = get('keys_move', {
    'QWERTY': (pg.K_a, pg.K_w, pg.K_d, pg.K_s, pg.K_q, pg.K_e, pg.K_x, pg.K_z),
    'Dvorak': (pg.K_a, pg.K_COMMA, pg.K_e, pg.K_o, (pg.K_SLASH, pg.K_QUOTE),
               pg.K_PERIOD, pg.K_q, pg.K_SEMICOLON)
})
KB_LAYOUTS = KEYS_MOVE.keys()
KB_LAYOUT = get('kb_layout', 'QWERTY')
ks = []
def ks (i, extra = ()):
    rtn = {}
    for layout in KB_LAYOUTS:
        k = KEYS_MOVE[layout][i]
        rtn[layout] = ((k,) if isinstance(k, int) else k) + extra
    return rtn
KEYS_MOVE_LEFT = ks(0, KEYS_LEFT)
KEYS_MOVE_UP = ks(1, KEYS_UP)
KEYS_MOVE_RIGHT = ks(2, KEYS_RIGHT)
KEYS_MOVE_DOWN = ks(3, KEYS_DOWN)
KEYS_MOVE_UPLEFT = ks(4)
KEYS_MOVE_UPRIGHT = ks(5)
KEYS_MOVE_DOWNRIGHT = ks(6)
KEYS_MOVE_DOWNLEFT = ks(7)
del ks
KEYS_MULTI = get('keys_multi', pg.KMOD_CTRL)

KEYS_MINIMISE = get('keys_minimise', (pg.K_F10,))
KEYS_FULLSCREEN = get('keys_fullscreen', (pg.K_F11,
    (pg.K_RETURN, pg.KMOD_ALT, True), (pg.K_KP_ENTER, pg.KMOD_ALT, True)))
KEYS_BACK = get('keys_back', (pg.K_BACKSPACE, pg.K_ESCAPE))
KEYS_NEXT = get('keys_next', (pg.K_SPACE, pg.K_RETURN, pg.K_KP_ENTER))
KEYS_NEXT_NONPRINTABLE = get('keys_next', (pg.K_RETURN, pg.K_KP_ENTER))
KEYS_ALTER_LEFT = get('keys_alter_left', ((pg.K_LEFT, 0, True),))
KEYS_ALTER_RIGHT = get('keys_alter_right', ((pg.K_RIGHT, 0, True),))
KEYS_ALTER_LEFT_BIG = get('keys_alter_left_big',
                          ((pg.K_LEFT, pg.KMOD_ALT, True),))
KEYS_ALTER_RIGHT_BIG = get('keys_alter_right_big',
                           ((pg.K_RIGHT, pg.KMOD_ALT, True),))
KEYS_ALTER_HOME = get('keys_alter_home', ((pg.K_LEFT, pg.KMOD_CTRL, True),))
KEYS_ALTER_END = get('keys_alter_end', ((pg.K_RIGHT, pg.KMOD_CTRL, True),))
KEYS_RESET = get('keys_reset', ((pg.K_r, 0, True),))
KEYS_TAB = get('keys_tab', (pg.K_TAB, pg.K_F8, pg.K_SLASH, pg.K_BACKSLASH))
KEYS_INSERT = get('keys_insert', KEYS_NEXT + (pg.K_i, pg.K_INSERT))
KEYS_DEL = get('keys_del', (pg.K_DELETE, pg.K_d))
KEYS_UNDO = get('keys_undo', ((pg.K_u, 0, True), (pg.K_z, pg.KMOD_CTRL, True)))
KEYS_REDO = get('keys_redo', ((pg.K_r, pg.KMOD_CTRL, True),
                              (pg.K_y, pg.KMOD_CTRL, True),
                              (pg.K_z, (pg.KMOD_CTRL, pg.KMOD_SHIFT), True)))

MOVE_INITIAL_DELAY = get('move_initial_delay', 2. / FPS)
MOVE_REPEAT_DELAY = 1. / FPS # shouldn't be edited: required for some puzzles
MENU_INITIAL_DELAY = get('menu_initial_delay', .3)
MENU_REPEAT_DELAY = get('menu_repeat_delay', .15)

# menu
PUZZLE_TEXT_UPPER = get('puzzle_text_upper', True)
PRINTABLE_L = [c for c in string.printable if c not in string.whitespace]
PRINTABLE_L.append(' ')
PRINTABLE = get('printable_l', PRINTABLE_L)
PRINTABLE = set(PRINTABLE_L)
PRINTABLE = get('printable', PRINTABLE)
IGNORED_ACCESS_KEY_CHARS = get('ignored_access_key_chars', ' ')
MIN_CHAR_ID = get('min_char_id', 32)
MAX_CHAR_ID = get('max_char_id', 255)
SELECTED_CHAR_ID_OFFSET = get('selected_char_id_offset', 256)
SPECIAL_CHAR_ID_OFFSET = get('special_char_id_offset', 512)
DEFAULT_SELECT_ORDER = 0 # 0 for rows take precedence, 1 for columns
LEVEL_SELECT_COLS = get('level_select_cols', 5)
POST_SOLVE_WAIT = get('post_solve_wait', 1000)
NUM_UNCOMPLETED_LEVELS = get('num_uncompleted_levels', 5)
# (small, mid, large, very large)
# < 1 means fraction of total number of options, >= 1 means absolute value
SELECT_STEP = get('select_step', (1, .01, 5, .05))
MIN_SELECT_STEP = get('min_select_step', (1, 1, .01, 5))

# puzzle
FORCE_MOVE = get('force_move', 2)
FORCE_ARROW = FORCE_MOVE # some puzzles are impossible/too easy if different
SOLVE_SPEED = get('solve_speed', 5) # delay between moves in frames
END_SOLVE_DELAY = get('end_solve_delay', 10)
FF_SPEEDUP = get('ff_speedup', 4)
SOLN_DIRS = get('soln_dirs', 'lurd')
SOLN_DIRS_SHOWN = get('soln_dirs_shown', SOLN_DIRS.upper())

# messages
SHOW_MSG = get('show_msg', 1)
# proportion of smaller screen dimension
MSG_LINE_HEIGHT = get('msg_line_height', .1)
MSG_PADDING_TOP = get('msg_padding_top', .02)
MSG_PADDING_BOTTOM = get('msg_padding_bottom', .01)
MSG_MAX_HEIGHT = get('msg_max_height', .2) # proportion of screen height

# help messages
HELP_MSG_POOLS = get('help_msg_pools', {
    'default': [
        'Are you sure you\'ve thought this through?',
        'Do you really want to stoop this low?',
        'Wheeeeeeeeeeeee!',
        'It\'s not that hard, I promise.'
    ], 'low_time': [
        'I hope you got here by accident.',
        'Not going to think about it for a bit first?',
        'You\'re kidding, right?'
    ], 'high_autosolve': [
        'Do you intend to play the game yourself at all?',
        'Getting lazy again?',
        'I should start charging for these solutions.',
        'I knew you\'d be back.',
        'Hey, you have to do some of the work.'
    ], 'no_recent_autosolve': [
        'Phew, I was getting worried you might be getting clever.',
        'It\'s been a while...'
    ]
})
HELP_MSG_POOL_NAMES = get('help_msg_pool_names',
    ('default', 'low_time', 'high_autosolve', 'no_recent_autosolve'))
HELP_MSG_WEIGHTING_FNS = get('help_msg_weighting_fn', {
    # always 1
    'default': lambda x: 1,
    # high towards 0, 1 at 60, 0 past 180
    'low_time': lambda t: 90 * (1. / t - 1. / 180),
    # 0 before 1/4, 1 at 1/2
    'high_autosolve': lambda r: (16. / 3) * max(r, 1. / 4) ** 2 - 1. / 3,
    # 0 before 5, 1 at 10
    'no_recent_autosolve': lambda n: (1. / 875) * n ** 3 - 1. / 7
})
HELP_MSG_MIN_SOLVED = get('help_msg_min_solved', 5)
SOLVE_HISTORY_SIZE = get('solve_history_size', 20)

# editor
EDITOR_WIDTH = get('editor_width', .7) # proportion of screen width
BLANK_LEVEL = get('blank_level', '5 5')
UNDO_LEVELS = get('undo_levels', 0)
RESIZE_DEAD_ZONE_BOUNDARY = get('resize_dead_zone_boundary', .4)
RESIZE_LENGTH = get('resize_speed', .07)
LEVEL_NAME_LENGTH = get('level_name_length', 6)
EDITOR_ARROW_PADDING = get('editor_arrow_padding', .05) # eats into editor

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
B_PORTAL = 5

WALL = 99

# appearance
THEMES = ('default',)
DEFAULT_THEME = get('default_theme', 'default')
THEME = get('theme', DEFAULT_THEME)
# menu
RAND_B_RATIO = get('rand_b_ratio', {
    'default': .1
})
RAND_S_RATIO = get('rand_s_ratio', {
    'default': .1
})
# puzzle
PUZZLE_FONT = get('puzzle_font', {
    'default': 'orbitron-black.otf'
})
PUZZLE_TEXT_COLOUR = get('puzzle_text_colour', {
    'default': (0, 0, 0)
})
PUZZLE_TEXT_SELECTED_COLOUR = get('puzzle_text_selected_colour', {
    'default': (255, 0, 0)
})
PUZZLE_TEXT_SPECIAL_COLOUR = get('puzzle_text_special_colour', {
    'default': (0, 180, 0)
})
MSG_FONT = get('msg_font', {
    'default': 'orbitron-black.otf'
})
MSG_TEXT_COLOUR = get('msg_text_colour', {
    'default': (0, 0, 0)
})
PUZZLE_LINE_COLOUR = get('puzzle_line_colour', {
    'default': (200, 200, 200)
})
PUZZLE_LINE_WIDTH = get('puzzle_line_width', {
    'default': 1
})
PUZZLE_BORDER_WIDTH = get('puzzle_border_width', {
    'default': 1
})
# selection
SEL_COLOUR = get('sel_colour', {
    'default': (255, 0, 0)
})
SECONDARY_SEL_COLOUR = get('secondary_sel_colour', {
    'default': (255, 100, 100)
})
MIN_SEL_WIDTH = get('min_sel_width', {
    'default': 1
})
SEL_WIDTH = get('sel_width', { # proportion of tile size
    'default': .05
})
# colours
BG = get('bg', {
    'default': (255, 255, 255)
})
SURFACE_COLOURS = get('surface_colours', {
    'default': {
        S_BLANK: (255, 255, 255),
        S_SLIDE: (150, 150, 255),
        S_LEFT: (90, 90, 90),
        S_UP: (50, 50, 50),
        S_RIGHT: (130, 130, 130),
        S_DOWN: (170, 170, 170)
    }
})
BLOCK_COLOURS = get('block_colours', {
    'default': {
        B_PLAYER: (128, 16, 7),
        B_IMMOVEABLE: (43, 40, 33),
        B_STANDARD: (95, 60, 27),
        B_SLIDE: (209, 209, 255),
        B_BOUNCE: (126, 176, 38)
    }
})

# audio
MUSIC_VOLUME = get('music_volume', 50)
EVENT_ENDMUSIC = pg.USEREVENT
SOUND_VOLUME = get('sound_volume', 50)
SOUND_THEMES = set()
for d in (SOUND_DIR, MUSIC_DIR):
    try:
        SOUND_THEMES = SOUND_THEMES.union(os.listdir(d))
    except OSError:
        # directory doesn't exist
        pass
SOUND_THEMES.add('none')
SOUND_THEMES = sorted(SOUND_THEMES)
SOUND_THEME = get('sound_theme', 'default')
SOUNDS = {'move': 1, 'hit': 1, 'wall': 1}
SOUND_VOLUMES = {}
SIMUL_SNDS = 5 # for same base ID
TOTAL_SIMUL_SNDS = 8


def set (**settings):
    """Save the value of a setting to file.

set(**settings)

key: the setting's name; case-insensitive.
value: the value to store.  This must have the property that
       eval(repr(value)) == value.

"""
    for key, value in settings.iteritems():
        self = sys.modules[__name__]
        setattr(self, key.upper(), value)
        _local[key.upper()] = repr(value)
        save_conf()
    # hack: delete settings stored here first, so loading settings doesn't get
    # previous ones in the module (and need to ignore __name__, for example)
    for attr in [a for a in vars(self).keys() if not a.startswith('__')]:
        delattr(self, attr)
    # reload this module to ensure settings depending on this one are updated
    reload(self)