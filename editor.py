import pygame
import evthandler as eh

import menu
from puzzle import Puzzle
import conf

# TODO:
# document
# insert:
#  tab to another grid containing every block/goal/surface and KEY_CONTINUE or K_i on main grid to insert; or
#  press a number to insert that ID and use b/g/s to switch between block, goal and surface modes
# undo/redo with u/v (store grid each step up to conf.UNDO_LEVELS and just restore then set puzzle dirty)
# reset to blank with r
# quicksave with q - no need to solve, goes into drafts, gets autonamed
# save menu option (doesn't quit)
# menu should have new/edit, then under each puzzle get play/edit/delete/rename

class PauseMenu (menu.Menu):
    def init (self):
        menu.Menu.init(self, (
            (
                menu.Button('Continue', self.game.quit_backend),
                menu.Button('Save', self.set_page, 1),
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
        event_handler.add_key_handlers([
            (conf.KEYS_LEFT, [(self.move, (0,))]) + args,
            (conf.KEYS_UP, [(self.move, (1,))]) + args,
            (conf.KEYS_RIGHT, [(self.move, (2,))]) + args,
            (conf.KEYS_DOWN, [(self.move, (3,))]) + args,
            (conf.KEYS_BACK, self.pause, eh.MODE_ONDOWN)
        ])
        self.event_handler = event_handler

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
        self.puzzle = Puzzle(self.game, definition, border = 1)
        self.puzzle.select(0, 0)
        self.puzzle.grid[0][0][2] = True
        self.dirty = True

    def insert (self, event):
        if event.key in conf.KEYS_NUM:
            print 'insert', event.unicode

    def move (self, event, direction):
        self.puzzle.move_selected(direction)

    def pause (self, event = None):
        self.game.start_backend(PauseMenu)

    def update (self):
        pass

    def draw (self, screen):
        if self.dirty:
            screen.fill(conf.BG)
        drawn = self.puzzle.draw(screen, self.dirty, screen.get_size())
        self.dirty = False
        return drawn