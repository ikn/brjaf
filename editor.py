import pygame
import evthandler as eh

import menu
from puzzle import Puzzle, BoringBlock
import conf

# TODO:
# document
# insert:
#  tab to another grid containing every block/goal/surface and KEY_CONTINUE or K_i on main grid to insert; or
#  press a number to insert that ID and use b/g/s to switch between block, goal and surface modes
# undo/redo with u/ctrl-u (store grid each step up to conf.UNDO_LEVELS and just restore then set puzzle dirty)
# reset to blank with r
# quicksave with q - no need to solve, goes into drafts, gets autonamed
# save menu option (doesn't quit) (reject if no B_PLAYER or already winning or can't solve)

class PauseMenu (menu.Menu):
    def init (self, editor):
        menu.Menu.init(self, (
            (
                menu.Button('Continue', self.game.quit_backend),
                menu.Button('Save', editor.save),
                menu.Button('Quit', self.game.quit_backend, 2)
            ),
        ))

class Editor:
    def __init__ (self, game, event_handler, ID = None):
        # add event handlers
        event_handler.add_event_handlers({pygame.KEYDOWN: self.insert})
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
            (conf.KEYS_BACK, self.pause, od),
            (conf.KEYS_TAB, self.switch_puzzle, od),
            (conf.KEYS_INSERT, self.insert_simple, od),
            (conf.KEYS_DEL, self.del_block, od)
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
        # load a level
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

    def move (self, key, event, mods, direction):
        """Callback for arrow keys."""
        mods = (mods & conf.MOD_SHIFT, mods & conf.MOD_ALT)
        shrink = mods[direction <= 1]
        grow = mods[direction > 1]
        if shrink ^ grow:
            self.editor.resize(1 if grow else -1, direction)
            self.dirty = True
        else:
            # move selection
            self.puzzle.move_selected(direction)

    def pause (self, *args):
        self.game.start_backend(PauseMenu, self)

    def switch_puzzle (self, *args):
        self.editing = not self.editing
        if self.editing:
            self.puzzle = self.editor
        else:
            self.puzzle = self.selector
        self.dirty = True

    def insert_simple (self, *args):
        if not self.editing:
            return
        # get type and ID of selected tile in selector puzzle
        col, row = self.selector.selected
        x, y = self.editor.selected
        is_block = col == 0 and row <= conf.MAX_ID
        if is_block:
            ID = row
        elif col == 1:
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

    def insert (self, event):
        if not self.editing or event.key not in conf.KEYS_NUM:
            return
        print 'insert', event.unicode

    def del_block (self, *args):
        """Delete any block in the currently selected tile."""
        if self.editing:
            self.editor.rm_block(None, *self.editor.selected)

    def save (self):
        print '\'' + self.editor.definition() + '\''

    def update (self):
        pass

    def draw (self, screen):
        if self.dirty:
            screen.fill(conf.BG)
        drawn = self.puzzle.draw(screen, self.dirty, screen.get_size())
        self.dirty = False
        return drawn