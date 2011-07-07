import pygame
import evthandler as eh

import menu
from puzzle import Puzzle, BoringBlock
import level
import conf

# TODO:
# save menu option (can save in drafts, though)
# level message, solution
# new solution format: t,m,t,m,t,...m
    # t is number of frames to wait; can be omitted to default to some setting ('solution speed')
    # m is move to make on the next frame (has >=1 of l/u/r/d)
    # solution lines start with : and first one, given by solving, is 'primary' solution
    # can also add more solutions later; these are viewed through some 'watch solutions' menu for each puzzle
    # replaying solutions should support manual advance to the next input frame and display current frame's input at bottom

class SolveMenu (menu.Menu):
    """The pause menu for solving a created level."""

    def init (self, level):
        menu.Menu.init(self, (
            (
                menu.Button('Continue', self.game.quit_backend),
                menu.Button('Quit', self.game.quit_backend, 2)
            ),
        ))

class Menu (menu.Menu):
    """The editor pause menu."""

    def init (self, editor):
        self._default_selections[1] = (0, 2)
        menu.Menu.init(self, (
            (
                menu.Button('Continue', self.game.quit_backend),
                menu.Button('Save', self._save, editor),
                menu.Button('Reset', self.set_page, 1),
                menu.Button('Quit', self.game.quit_backend, 2)
            ), (
                menu.Text('Reset?'),
                menu.Button('Yes', self._reset, editor),
                menu.Button('No', self.back)
            ), (
                menu.Text('There must be'),
                menu.Text('at least one'),
                menu.Text('player block.')
            ), (
                menu.Text('The puzzle starts'),
                menu.Text('with the player'),
                menu.Text('already winning.')
            )
        ))

    def _level_won (self):
        # callback for solving the created level
        print '\'' + self._defn + '\''
        del self._defn
        self.game.quit_backend()

    def _save (self, editor):
        # try to save the current puzzle
        # check if there's a player block
        if not any(b.type == conf.B_PLAYER for b in editor.editor.blocks):
            self.set_page(2)
            return
        # check if already winning: create a puzzle and run it for one frame
        defn = editor.history[editor.state]
        if level.defn_wins(defn):
            self.set_page(3)
            return
        # ask the player to solve the puzzle
        self._defn = defn
        self.game.quit_backend()
        self.game.start_backend(level.LevelBackend, None, defn, SolveMenu,
                                self._level_won)

    def _reset (self, editor):
        editor._do_reset()
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
del_block
undo
redo
menu
reset

    ATTRIBUTES

game: Game instance.
selector: puzzle used to select blocks/surfaces to add.
editor: the puzzle being edited.
puzzle: the current visible puzzle (editor or selector).
editing: whether the current puzzle is editor.
history: a list of past puzzle definitions.
state: the current position in the history.

"""

    def __init__ (self, game, event_handler, ID = None):
        # add event handlers
        self.game = game
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
            (conf.KEYS_DEL, self.del_block, od),
            (conf.KEYS_UNDO, self.undo) + menu_args,
            (conf.KEYS_REDO, self.redo) + menu_args,
            (conf.KEYS_RESET, self.reset, od)
        ])
        self.event_handler = event_handler

        # create block/surface selection grid
        blocks = xrange(conf.MAX_ID + 1)
        surfaces = xrange(-1, conf.MIN_ID - 1, -1)
        definition = '3 {0}\n{1}\n\n{2}\n{3}'.format(
            max(len(blocks), len(surfaces)),
            '\n'.join('{0} 0 {1}'.format(b, i) for i, b in enumerate(blocks)),
            '\n'.join('{0} 1 {1}'.format(b, i) for i, b in enumerate(blocks)),
            '\n'.join('{0} 2 {1}'.format(s, i) for i, s in enumerate(surfaces))
        )
        self.selector = Puzzle(game, definition, border = 1)
        self.selector.select(0, 0)

        self.FRAME = conf.FRAME
        self.load(ID)

    def load (self, ID = None):
        """Load a level with the given custom level ID, else a blank level."""
        if ID is None:
            # blank grid
            definition = conf.BLANK_LEVEL
        else:
            # get data from file
            path = conf.LEVEL_DIR_CUSTOM if ID[0] else conf.LEVEL_DIR_MAIN
            with open(path + str(ID[1])) as f:
                definition = f.read()
        self.editor = Puzzle(self.game, definition, border = 1)
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

    def switch_puzzle (self, *args):
        """Switch selected puzzle between editor and block selector."""
        self.editing = not self.editing
        if self.editing:
            self.puzzle = self.editor
        else:
            self.puzzle = self.selector
        self.dirty = True

    def insert (self):
        """Insert a block or surface at the current position."""
        if not self.editing:
            return
        # get type and ID of selected tile in selector puzzle
        col, row = self.selector.selected
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
        # make changes to selected tile in editor puzzle
        if is_block:
            self.editor.add_block((BoringBlock, ID), x, y)
        else:
            self.editor.set_surface(x, y, ID)
        self.store_state()

    def _insert_cb (self, *args):
        # callback for conf.KEYS_INSERT
        if self.editing:
            self.insert()
        else:
            self.switch_puzzle()

    def del_block (self, *args):
        """Delete any block in the currently selected tile."""
        if self.editing:
            self.editor.rm_block(None, *self.editor.selected)
            self.store_state()

    def undo (self, *args):
        """Undo changes to the puzzle."""
        if self.state > 0:
            self.load_state(self.state - 1)

    def redo (self, *args):
        """Redo undone changes."""
        if self.state < len(self.history) - 1:
            self.load_state(self.state + 1)

    def menu (self):
        """Show the editor menu."""
        self.game.start_backend(Menu, 0, self)

    def _back_cb (self, *args):
        # callback for conf.KEYS_BACK
        if self.editing:
            self.menu()
        else:
            self.switch_puzzle()

    def _do_reset (self):
        # actually reset the puzzle
        # just reset to original state - to whatever was loaded, if anything
        self.load_state(0)
        self.history = [self.history[0]]

    def reset (self, *args):
        """Confirm resetting the puzzle."""
        self.game.start_backend(Menu, 1, self)

    def update (self):
        """Do nothing (needed by Game)."""
        pass

    def draw (self, screen):
        """Draw the puzzles."""
        if self.dirty:
            screen.fill(conf.BG)
        drawn = self.puzzle.draw(screen, self.dirty)
        self.dirty = False
        return drawn