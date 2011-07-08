from glob import glob

import evthandler as eh

import menu
from puzzle import Block, Puzzle
import conf

# TODO:
# solutions:
#   confirmation; something random (have criteria):
#       "Are you sure you've thought this through?"
#       "Do you intend to play the game yourself at all?" (used solutions often)
#       "Getting lazy again?" (used solutions often)
#       "Phew, I was getting worried you might be getting clever." (used solutions, but not recently)
#       "Not going to think about it for a bit first?" (haven't spent long on the puzzle)
#       "I should start charging for these solutions." (used solutions often)
#       "I knew you'd be back." (used solutions often)
#       "I hope you got here by accident." (haven't spent long on the puzzle)
#       "Do you really want to stoop this low?"
#       "Hey, you have to do some of the work." (used solutions often)
#       "Wheeeeeeeeeeeee!"
#       "It's not that hard, I promise."
#   "Keep trying" / "Solve it for me"

def get_levels (custom = False):
    """Get a list of existing levels.

Takes a boolean determining whether to load custom levels.

"""
    path = conf.LEVEL_DIR_CUSTOM if custom else conf.LEVEL_DIR_MAIN
    return sorted(lvl[len(path):] for lvl in glob(path + '*'))

def defn_wins (defn):
    """Check if the given definition starts in a winning state."""
    lvl = Level(None, None, defn)
    # need to simulate for two frames to be sure (something might move)
    lvl.update()
    lvl.update()
    return lvl.won

class PauseMenu (menu.Menu):
    """The standard pause menu when playing a level.

Takes the LevelBackend instance.

"""

    def init (self, level):
        menu.Menu.init(self, ((
            menu.Button('Continue', self.game.quit_backend),
            menu.Button('Help', level.solve),
            menu.Button('Quit', self.game.quit_backend, 2)
        ),))

class Level (object):
    """A simple Puzzle wrapper to handle drawing.

    CONSTRUCTOR

Level([event_handler][, ID][, definition][, win_cb])

event_handler: evthandler.EventHandler instance to use for keybindings.  If not
               given, the level cannot be controlled by the keyboard.
ID: level ID to load in the form (is_custom, level_ID).
definition: a level definition to use; see the puzzle module for details.
win_cb: function to call when the player wins.

One of ID and definition is required.

    METHODS
load
move
reset
solve

    ATTRIBUTES

game: None.
ID: level ID; None if this is a custom level or a definition was given instead.
puzzle: puzzle.Puzzle instance.
players: player blocks in the puzzle.
msg: puzzle message.
solving: whether the puzzle is currently being solved.
solving_index: the current step in the solution being used to solve the puzzle.
win_cb: as given.

"""

    def __init__ (self, event_handler = None, ID = None, definition = None,
                  win_cb = None):
        if not hasattr(self, 'game'):
            self.game = None
        if event_handler is not None:
            # add gameplay key handlers
            args = (
                eh.MODE_ONDOWN_REPEAT,
                max(int(conf.MOVE_INITIAL_DELAY * conf.FPS), 1),
                max(int(conf.MOVE_REPEAT_DELAY * conf.FPS), 1)
            )
            event_handler.add_key_handlers([
                (conf.KEYS_LEFT, [(self._move, (0,))]) + args,
                (conf.KEYS_UP, [(self._move, (1,))]) + args,
                (conf.KEYS_RIGHT, [(self._move, (2,))]) + args,
                (conf.KEYS_DOWN, [(self._move, (3,))]) + args,
                (conf.KEYS_BACK, self.pause, eh.MODE_ONDOWN),
                (conf.KEYS_RESET, self.reset, eh.MODE_ONDOWN)
            ])
        self.load(ID, definition)
        self.win_cb = win_cb

    def load (self, ID = None, definition = None):
        """Load a level.

Takes ID and definition arguments as in the constructor.

"""
        self.ID = None if ID is None or ID[0] else ID[1]
        if ID is not None:
            # get data from file
            path = conf.LEVEL_DIR_CUSTOM if ID[0] else conf.LEVEL_DIR_MAIN
            with open(path + ID[1]) as f:
                definition = f.read()
        self.puzzle = Puzzle(self.game, definition, True, border = 1)
        self.players = [b for b in self.puzzle.blocks
                        if b.type == conf.B_PLAYER]
        # store message and solutions
        lines = definition.split('\n')
        msgs = []
        solns = []
        for line in lines:
            line = line.strip()
            for char, val in (('@', msgs), (':', solns)):
                if line.startswith(char):
                    # add lines (stripped) starting with the character
                    val.append(line[1:].strip())
                    # won't start with the other one if it starts with this one
                    continue
        self.msg = msgs[0] if msgs else None
        self._solutions = solns

        self._winning = False
        self.won = False
        self.solving = False
        self.solving_index = None
        self.dirty = True

    def move (self, *directions):
        """Apply force to all player blocks in the given directions."""
        for d in set(directions):
            for player in self.players:
                player.add_force(d, conf.FORCE_MOVE)

    def _move (self, key, event, mods, direction):
        # key callback to move player
        if not self.solving:
            self.move(direction)

    def reset (self, *args):
        """Reset the level to its state after the last call to Level.load."""
        if not self.solving:
            self.puzzle.init()
            self.players = [b for b in self.puzzle.blocks
                            if b.type == conf.B_PLAYER]

    def _parse_soln (self, ID):
        # parse a solution string if not already done, and return the result
        soln = self._solutions[ID]
        if isinstance(soln, list):
            # already parsed
            return soln
        parsed = []
        dirs = ('l', 'u', 'r', 'd')
        for i, s in enumerate(soln.split(',')):
            if i % 2:
                # directions
                s = [dirs.index(c) for c in s]
            else:
                # time delay
                s = int(s) if s else conf.SOLVE_SPEED
            parsed.append(s)
        self._solutions[ID] = parsed
        return parsed

    def solve (self, solution = 0):
        """Solve the puzzle.

Takes the solution number to use (its index in the list of solutions ordered as
in the puzzle definition).

"""
        if self.solving_index is None:
            # starting
            self.reset()
            self.solving = True
            self.solving_index = 0
            self._solution = self._parse_soln(solution)
            self._solve_time = self._solution[0]
        elif self.solving_index == len(self._solution):
            # finished
            self.solving = False
            self.solving_index = None
            del self._solution
        else:
            # continuing
            print self._solution[self.solving_index]
            self.solving_index += 1

    def update (self):
        """Update puzzle and check win conditions."""
        self.puzzle.step()
        # check for surfaces with their corresponding Block types on them
        win = True
        for col in self.puzzle.grid:
            for s, b, sel in col:
                # goal surfaces have IDs starting at 0
                if s >= 0 and (not isinstance(b, Block) or s != b.type):
                    win = False
                    break
        # need to stay winning for one frame - that is, blocks must have
        # stopped on the goals, not just be moving past them
        if win:
            if self._winning:
                # if this is the first frame since we've won,
                if not self.won:
                    # save to disk
                    if self.ID is not None and not self.won:
                        levels = conf.get('completed_levels', [])
                        if self.ID not in levels:
                            levels.append(self.ID)
                            conf.set('completed_levels', levels)
                            self.game.set_backend_attrs(menu.MainMenu,
                                                        're_init', True)
                    # call win callback
                    if self.win_cb is not None:
                        self.win_cb()
                self.won = True
            else:
                self._winning = True
        else:
            self._winning = False
        # continue solving
        if self.solving:
            self.solve()

    def _mk_msg (self, screen, w, h):
        # draw message to screen
        if self.msg is None:
            return
        # keep message size proportional to screen size (ss)
        ss = min(w, h)
        font = [conf.MSG_FONT, ss * conf.MSG_LINE_HEIGHT, False]
        args = (self.msg, conf.MSG_TEXT_COLOUR, None, w, 0, True)
        # reduce font size until fits in screen width/proportion of height
        target_height = h * conf.MSG_MAX_HEIGHT
        while font[1] > 0:
            try:
                msg = self.game.fonts.text(font, *args)
            except ValueError:
                pass
            else:
                if msg.get_size()[1] <= target_height:
                    break
            font[1] -= 1
        if font[1] > 0:
            msg_w, self.msg_h = msg.get_size()
            # centre message horizontally
            blit_w = (w - msg_w) / 2
            blit_h = h - self.msg_h - ss * conf.MSG_PADDING_BOTTOM
            screen.blit(msg, (blit_w, blit_h))
        # else couldn't make font size small enough to fit the message
        # on the screen (_very_ unlikely): just don't display it

    def draw (self, screen):
        """Draw the puzzle."""
        w, h = screen.get_size()
        # keep message size proportional to screen size (ss)
        ss = min(w, h)
        if self.dirty:
            screen.fill(conf.BG)
            # generate message, if any
            self._mk_msg(screen, w, h)
        if self.msg is not None:
            # reduce puzzle size to fit in message
            padding = ss * (conf.MSG_PADDING_TOP + conf.MSG_PADDING_BOTTOM)
            h -= self.msg_h + padding
        drawn = self.puzzle.draw(screen, self.dirty, (w, h))
        self.dirty = False
        return drawn

class LevelBackend (Level):
    """A wrapper for Level to make it a Game backend.

    CONSTRUCTOR

LevelBackend(game, event_handler[, ID][, definition],
             pause_menu = PauseMenu, win_cb = game.quit_backend)

pause_menu: menu.Menu subclass to instantiate on pausing.  Its init method is
            passed this LevelBackend instance.

ID, definition and win_cb are as taken by Level.

    METHODS

pause

    ATTRIBUTES

game: Game instance.
pause_menu: as given.

"""

    def __init__ (self, game, event_handler, ID = None, definition = None,
                  pause_menu = PauseMenu, win_cb = 'default'):
        self.game = game
        self.event_handler = event_handler
        self.FRAME = conf.FRAME
        self.pause_menu = pause_menu
        if win_cb == 'default':
            win_cb = game.quit_backend
        Level.__init__(self, event_handler, ID, definition, win_cb)

    def pause (self, *args):
        """Show the pause menu."""
        if self.pause_menu is not None:
            self.game.start_backend(self.pause_menu, None, self)