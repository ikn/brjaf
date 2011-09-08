import os

import pygame
import evthandler as eh

import menu
from puzzle import Puzzle, BoringBlock
import level
import conf

# TODO:
# - 'Save draft' option
# - save level message

class SolveMenu (menu.Menu):
    """The pause menu for solving a created level.

Takes the Level backend instance.

"""

    def init (self, level):
        menu.Menu.init(self, ((
            menu.Button('Continue', self.game.quit_backend),
            menu.Button('Quit', self.game.quit_backend, 2)
        ),))


def success_cb (fn, editor):
    """Callback for SaveMenu on successful save.

This function shows a notification and sets the current level ID to the name
given to the level.

"""
    editor.ID = fn
    editor.game.start_backend(Menu, 4, editor)
    # refresh entries in main menu
    editor.game.set_backend_attrs(menu.MainMenu, 're_init', True)

class SaveMenu (menu.Menu):
    """Menu for saving a created level.

Further arguments: (directory, defn, fn = ''[, success_cb[, success_cb_args]])

directory: directory to save in.
defn: level definition to save.
fn: text to initialise filename text entry with.
success_cb: a function to call with the filename the level is saved under on
            success.
success_cb_args: list of arguments to pass to success_cb after the filename.

"""

    def __init__ (self, *args, **kw):
        menu.Menu.__init__(self, *args, **kw)
        self._entry.toggle_focus()

    def init (self, directory, defn, fn = '', success_cb = None,
              success_cb_args = ()):
        if not fn:
            fn = ''
        # most bad characters will be caught when we try to create the file,
        # but space would create problems in listing the names, os.sep
        # would create files in directories if they exist, and : does weird
        # things without errors on Windows
        not_allowed = ' :' + os.sep
        allowed = set(c for c in conf.PRINTABLE if c not in not_allowed)
        self._entry = menu.TextEntry(conf.LEVEL_NAME_LENGTH, fn, allowed)
        self.directory = directory
        self.defn = defn
        self._success_cb = success_cb
        self._success_cb_args = success_cb_args

        self._default_selections[2] = (0, 2)
        menu.Menu.init(self, (
            (
                menu.Text('Level name'),
                self._entry,
                menu.Button('Save', self._save),
                menu.Button('Cancel', self.game.quit_backend)
            ), (
                menu.Text('Level name'),
                menu.Text('is blank.')
            ), (
                menu.Text('Overwrite?'),
                menu.Button('Yes', self._save, True),
                menu.Button('No', self.back)
            ), (
                menu.Text('Invalid'),
                menu.Text('filename')
            ), (
                menu.Text('Can\'t write'),
                menu.Text('to that file.')
            )
        ))

    def _save (self, overwrite = False):
        """Callback for trying to save using the entered name."""
        d = self.directory
        fn = self._entry.text
        # check for blank filename
        if fn == '':
            self.set_page(1)
            return
        # confirm overwrite if exists
        if not overwrite and os.path.exists(d + fn):
            self.set_page(2)
            return
        # create parent
        if not os.path.exists(d):
            os.makedirs(d)
        # try to write
        try:
            with open(d + fn, 'w') as f:
                f.write(self.defn)
        except IOError, e:
            if e.errno == 22:
                # invalid filename
                self.set_page(3)
            else:
                # unknown error
                self.set_page(4)
            return
        # success
        self.game.quit_backend()
        if self._success_cb is not None:
            self._success_cb(fn, *self._success_cb_args)


class Menu (menu.Menu):
    """The editor pause menu.

Takes the Editor instance.

"""

    def init (self, editor):
        self._editor = editor
        self._default_selections[1] = (0, 2)
        menu.Menu.init(self, (
            (
                menu.Button('Continue', self.game.quit_backend),
                menu.Button('Save', self._save),
                menu.Button('Reset', self.set_page, 1),
                menu.Button('Quit', self.game.quit_backend, 2)
            ), (
                menu.Text('Reset?'),
                menu.Button('Yes', self._reset),
                menu.Button('No', self.back)
            ), (
                menu.Text('There must be'),
                menu.Text('at least one'),
                menu.Text('player block.')
            ), (
                menu.Text('The puzzle starts'),
                menu.Text('with the player'),
                menu.Text('already winning.')
            ), (
                menu.Text('Level saved.'),
                menu.Button('OK', self.back)
            )
        ))

    def _level_won (self):
        """Callback for solving the created level."""
        self.game.quit_backend()
        # retrieve solution and add to definition
        self._defn += '\n: ' + self._lvl.stop_recording()
        # ask for level name
        self.game.start_backend(SaveMenu, None, conf.LEVEL_DIR_CUSTOM,
                                self._defn, self._editor.ID, success_cb,
                                (self._editor,))
        del self._defn

    def _save (self):
        """Callback for 'save' option."""
        e = self._editor
        # try to save the current puzzle
        # check if there's a player block
        if not any(b.type == conf.B_PLAYER for b in e.editor.blocks):
            self.set_page(2)
            return
        # check if already winning: create a puzzle and run it for one frame
        defn = e.history[e.state]
        if level.defn_wins(defn):
            self.set_page(3)
            return
        # ask the player to solve the puzzle
        self._defn = defn
        self.game.quit_backend()
        # show message making it clear what's going on
        defn += '\n@Solve the level first.'
        self._lvl = self.game.start_backend(level.LevelBackend, None, defn,
                                      SolveMenu, self._level_won)
        self._lvl.start_recording()

    def _reset (self, editor):
        """Call back for 'reset' option."""
        self._editor._do_reset()
        self.game.quit_backend()


class Editor (object):
    """A puzzle editor (Game backend).

Takes a (custom) puzzle ID to load, else starts editing a blank puzzle.

    METHODS

load
store_state
move
switch_puzzle
insert
delete
undo
redo
menu
reset

    ATTRIBUTES

game: Game instance.
ID: as given.
selector: puzzle used to select blocks/surfaces to add.
editor: the puzzle being edited.
puzzle: the current visible puzzle (editor or selector).
editing: whether the current puzzle is editor.
history: a list of past puzzle definitions.
state: the current position in the history.

"""

    def __init__ (self, game, event_handler, ID = None):
        self.game = game
        # add event handlers
        event_handler.add_event_handlers({pygame.MOUSEBUTTONDOWN: self._click})
        pzl_args = (
            eh.MODE_ONDOWN_REPEAT,
            max(int(conf.MOVE_INITIAL_DELAY * conf.FPS), 1),
            max(int(conf.MOVE_REPEAT_DELAY * conf.FPS), 1)
        )
        menu_args = (
            eh.MODE_ONDOWN_REPEAT,
            max(int(conf.MENU_INITIAL_DELAY * conf.FPS), 1),
            max(int(conf.MENU_REPEAT_DELAY * conf.FPS), 1)
        )
        od = eh.MODE_ONDOWN
        held = eh.MODE_HELD
        event_handler.add_key_handlers([
            (conf.KEYS_LEFT, [(self.move, (0,))]) + pzl_args,
            (conf.KEYS_UP, [(self.move, (1,))]) + pzl_args,
            (conf.KEYS_RIGHT, [(self.move, (2,))]) + pzl_args,
            (conf.KEYS_DOWN, [(self.move, (3,))]) + pzl_args,
            (conf.KEYS_BACK, self._back_cb, od),
            (conf.KEYS_TAB, self.switch_puzzle, od),
            (conf.KEYS_INSERT, self._insert_cb, od),
            (conf.KEYS_DEL, self.delete, od),
            (conf.KEYS_UNDO, self.undo) + menu_args,
            (conf.KEYS_REDO, self.redo) + menu_args,
            (conf.KEYS_RESET, self.reset, od)
        ])
        self.event_handler = event_handler

        # create block/surface selection grid
        blocks = xrange(conf.MAX_ID + 1)
        surfaces = xrange(-1, conf.MIN_ID - 1, -1)
        self._selector_defn = '3 {0}\n{1}\n\n{2}\n{3}'.format(
            max(len(blocks), len(surfaces)),
            '\n'.join('{0} 0 {1}'.format(b, i) for i, b in enumerate(blocks)),
            '\n'.join('{0} 1 {1}'.format(b, i) for i, b in enumerate(blocks)),
            '\n'.join('{0} 2 {1}'.format(s, i) for i, s in enumerate(surfaces))
        )
        self.selector = Puzzle(game, self._selector_defn)
        self.selector.old_selected = (0, 0)

        self.FRAME = conf.FRAME
        self.load(ID)

    def load (self, ID = None):
        """Load a level with the given custom level ID, else a blank level."""
        if ID is None:
            # blank grid
            definition = conf.BLANK_LEVEL
            self.ID = None
        else:
            # get data from file
            path = conf.LEVEL_DIR_CUSTOM
            #path = conf.LEVEL_DIR_DRAFT if ID[0] else conf.LEVEL_DIR_CUSTOM
            with open(path + ID[1]) as f:
                definition = f.read()
            self.ID = ID[1]
        if hasattr(self, 'editor'):
            self.editor.load(definition)
        else:
            self.editor = Puzzle(self.game, definition)
        self.editor.select(0, 0)
        self.puzzle = self.editor
        self.editing = True
        self.dirty = True
        self.history = []
        self.state = -1
        self.store_state()

    def store_state (self):
        """Store the current state in history."""
        defn = self.editor.definition()
        # if nothing changed, return
        try:
            if self.history[self.state] == defn:
                return
        except IndexError:
            pass
        # purge 'future' states
        self.history = self.history[:self.state + 1]
        self.history.append(defn)
        # purge oldest state if need to (don't need to increment state, then)
        if len(self.history) > conf.UNDO_LEVELS > 0:
            self.history.pop(0)
        else:
            self.state += 1

    def load_state (self, state):
        """Load a previous state from history."""
        self.state = state
        # Puzzle.load returns whether it was resized
        if self.editor.load(self.history[state]):
            self.dirty = True

    def move (self, key, event, mods, direction):
        """Callback for arrow keys."""
        resize = False
        if self.editing:
            # can only resize if editing
            mods = (mods & pygame.KMOD_SHIFT, mods & pygame.KMOD_ALT)
            shrink = bool(mods[direction <= 1])
            grow = bool(mods[direction > 1])
            resize = shrink ^ grow
        if resize:
            # resize puzzle
            self.editor.resize(1 if grow else -1, direction)
            self.dirty = True
            self.store_state()
        else:
            # move selection
            self.puzzle.move_selected(direction)

    def insert (self):
        """Insert a block or surface at the current position."""
        if not self.editing:
            return
        # get type and ID of selected tile in selector puzzle
        col, row = self.selector.old_selected
        x, y = self.editor.selected
        is_block = col == 0 and row <= conf.MAX_ID
        if is_block:
            ID = row
        # will be here for col = 0 if past end of blocks
        elif col == 0 or col == 1:
            ID = row
            if ID > conf.MAX_ID:
                ID = conf.DEFAULT_SURFACE
        else:
            ID = -row - 1
            if ID >= 0:
                ID = conf.DEFAULT_SURFACE
        # make changes to selected tile in editor puzzle if necessary
        current = self.editor.grid[x][y]
        if is_block:
            if current[1] is None or current[1].type != ID:
                self.editor.add_block((BoringBlock, ID), x, y)
                self.game.play_snd('place_block')
        else:
            if current[0] != ID:
                self.editor.set_surface(x, y, ID)
                self.game.play_snd('place_surface')
        self.store_state()

    def _insert_cb (self, *args):
        """Callback for conf.KEYS_INSERT."""
        if self.editing:
            self.insert()
        else:
            self.switch_puzzle()

    def delete (self, *args):
        """Delete a block or surface in the currently selected tile."""
        if self.editing:
            x, y = self.editor.selected
            data = self.editor.grid[x][y]
            snd = True
            # delete block, if any
            if data[1] is not None:
                self.editor.rm_block(None, x, y)
                self.store_state()
            # set surface to blank if not already
            elif data[0] != conf.S_BLANK:
                self.editor.set_surface(x, y, conf.S_BLANK)
                self.store_state()
            else:
                snd = False
            if snd:
                self.game.play_snd('delete')

    def undo (self, *args):
        """Undo changes to the puzzle."""
        if self.state > 0:
            self.load_state(self.state - 1)

    def redo (self, *args):
        """Redo undone changes."""
        if self.state < len(self.history) - 1:
            self.load_state(self.state + 1)

    def _click (self, evt):
        """Handle mouse clicks."""
        if evt.button in (1, 3):
            # get clicked tile
            pos = self.editor.point_tile(evt.pos)
            if pos is not None:
                # clicked a tile in self.editor: select
                if not self.editing:
                    self.switch_puzzle()
                self.editor.select(*pos)
                if evt.button == 1:
                    # left-click to insert
                    self.insert()
                else:
                    # right-click to delete
                    self.delete()
            else:
                pos = self.selector.point_tile(evt.pos)
                if pos is not None:
                    # clicked a tile in self.selector: switch to selector, then
                    # select the tile
                    if self.editing:
                        self.switch_puzzle()
                    self.selector.select(*pos)

    def switch_puzzle (self, *args):
        """Switch selected puzzle between editor and block selector."""
        self.editing = not self.editing
        pzls = (self.editor, self.selector)
        if self.editing:
            new, old = pzls
        else:
            old, new = pzls
        # deselect old and select new
        old.old_selected = old.selected
        old.deselect()
        new.select(*new.old_selected)
        self.puzzle = new

    def reset (self, *args):
        """Confirm resetting the puzzle."""
        self.game.start_backend(Menu, 1, self)

    def menu (self):
        """Show the editor menu."""
        self.game.start_backend(Menu, 0, self)

    def _back_cb (self, *args):
        """Callback for conf.KEYS_BACK."""
        if self.editing:
            self.menu()
        else:
            self.switch_puzzle()

    def _do_reset (self):
        """Actually reset the puzzle."""
        # just reset to original state - to whatever was loaded, if anything
        self.load_state(0)
        self.history = [self.history[0]]

    def update (self):
        """Do nothing (needed by Game)."""
        pass

    def draw (self, screen):
        """Draw the puzzles."""
        if self.dirty:
            screen.fill(conf.BG[conf.THEME])
        # get puzzle sizes
        w, h = screen.get_size()
        w1 = int(conf.EDITOR_WIDTH * w)
        w2 = w - w1
        t = self.selector.tiler
        if w1 != t.offset[0]:
            # screen size changed: need to change selector offset; no need to
            # draw over area, as Game will have set self.dirty = True
            t.offset = [w1, 0]
            t.reset()
        # draw puzzles
        drawn1 = self.editor.draw(screen, self.dirty, (w1, h))
        drawn2 = self.selector.draw(screen, self.dirty, (w2, h))
        # and return the sum list of rects to draw in
        drawn = []
        for d in (drawn1, drawn2):
            if d:
                drawn += d
        if self.dirty:
            drawn = True
        self.dirty = False
        return drawn