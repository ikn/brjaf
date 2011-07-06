import pygame
import evthandler as eh

import menu
from puzzle import Puzzle, BoringBlock
import conf

# TODO:
# undo/redo with u/ctrl-u (store grid each step up to conf.UNDO_LEVELS and just restore then set puzzle dirty)
# reset to blank with r (confirm)
# quicksave with q - no need to solve, goes into drafts, gets autonamed (notify)
# save menu option (doesn't quit) (reject if no B_PLAYER or already winning or can't solve)
# level comment, solution
# new solution format: t,m,t,m,t,...m
    # t is number of frames to wait; can be omitted to default to some setting ('solution speed')
    # m is move to make on the next frame (has >=1 of l/u/r/d)
    # solution lines start with : and first one, given by solving, is 'primary' solution
    # can also add more solutions later; these are viewed through some 'watch solutions' menu for each puzzle
    # replaying solutions should support manual advance to the next input frame and display current frame's input at bottom

class Menu (menu.Menu):
    def init (self, editor):
        menu.Menu.init(self, (
            (
                menu.Button('Continue', self.game.quit_backend),
                menu.Button('Save', editor.save),
                menu.Button('Quit', self.game.quit_backend, 2)
            ),
        ))

class Editor (object):
    """A puzzle editor (Game backend).

Takes a (custom) puzzle ID to load, else starts editing a blank puzzle.

    METHODS

load
store_state
move
menu
switch_puzzle
insert
del_block
undo
save

    ATTRIBUTES

selector: puzzle used to select blocks/surfaces to add.
editor: the puzzle being edited.
history: a list of past puzzle definitions.
state: the current position in the history.

"""

    def __init__ (self, game, event_handler, ID = None):
        # add event handlers
        args = (
            eh.MODE_ONDOWN_REPEAT,
            max(int(conf.MOVE_INITIAL_DELAY * conf.FPS), 1),
            max(int(conf.MOVE_REPEAT_DELAY * conf.FPS), 1)
        )
        od = eh.MODE_ONDOWN
        held = eh.MODE_HELD
        event_handler.add_key_handlers([
            (conf.KEYS_LEFT, [(self.move, (0,))]) + args,
            (conf.KEYS_UP, [(self.move, (1,))]) + args,
            (conf.KEYS_RIGHT, [(self.move, (2,))]) + args,
            (conf.KEYS_DOWN, [(self.move, (3,))]) + args,
            (conf.KEYS_BACK, self.menu, od),
            (conf.KEYS_TAB, self.switch_puzzle, od),
            (conf.KEYS_INSERT, self.insert, od),
            (conf.KEYS_DEL, self.del_block, od),
            (conf.KEYS_UNDO, self.undo) + args
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

        self.game = game
        self.FRAME = conf.FRAME
        self.load(ID)

    def load (self, ID = None):
        """Load a level with the given ID, else a blank level."""
        self.ID = None if (ID is None or not ID[0]) else str(ID[1])
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
        self.history = self.history[:self.state + 2]
        self.history.append(defn)
        # purge oldest state if need to (don't need to increment state, then)
        if len(self.history) > conf.UNDO_LEVELS > 0:
            self.history.pop()
        else:
            self.state += 1
        print len(self.history)

    def move (self, key, event, mods, direction):
        """Callback for arrow keys."""
        resize = False
        if self.editing:
            # can only resize if editing
            mods = (mods & conf.MOD_SHIFT, mods & conf.MOD_ALT)
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

    def menu (self, *args):
        """Show the editor menu."""
        self.game.start_backend(Menu, self)

    def switch_puzzle (self, *args):
        """Switch selected puzzle between editor and block selector."""
        self.editing = not self.editing
        if self.editing:
            self.puzzle = self.editor
        else:
            self.puzzle = self.selector
        self.dirty = True

    def insert (self, *args):
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

    def del_block (self, *args):
        """Delete any block in the currently selected tile."""
        if self.editing:
            self.editor.rm_block(None, *self.editor.selected)
            self.store_state()

    def undo (self, key, event, mods):
        """Undo or redo changes to the puzzle."""
        do = False
        if mods & conf.MOD_CTRL:
            # redo
            if self.state < len(self.history) - 1:
                self.state += 1
                do = True
        else:
            # undo
            if self.state > 0:
                self.state -= 1
                do = True
        # Puzzle.load returns whether it was resized
        if do and self.editor.load(self.history[self.state]):
            self.dirty = True

    def save (self):
        """Show the menu to save the current puzzle."""
        print '\'' + self.history[self.state] + '\''

    def update (self):
        """Do nothing (needed by Game)."""
        pass

    def draw (self, screen):
        """Draw the puzzles."""
        if self.dirty:
            screen.fill(conf.BG)
        drawn = self.puzzle.draw(screen, self.dirty, screen.get_size())
        self.dirty = False
        return drawn