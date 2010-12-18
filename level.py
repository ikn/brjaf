from glob import glob

import evthandler as eh

import menu
from puzzle import Block, Puzzle
import conf

# TODO:
# document
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
#       "Do you _really_ want to stoop this low?"
#       "Hey, you have to do some of the work." (used solutions often)
#       "Wheeeeeeeeeeeee!"
#       "It's not that hard, I promise."
#   "Keep trying" / "Do it for me"

def get_levels (custom = False):
    path = conf.LEVEL_DIR_CUSTOM if custom else conf.LEVEL_DIR_MAIN
    return sorted(lvl[len(path):] for lvl in glob(path + '*'))

class Level:
    def __init__ (self, game, event_handler, ID = None, definition = None):
        # add gameplay key handlers
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
            (conf.KEYS_BACK, self.pause, eh.MODE_ONDOWN),
            (conf.KEYS_RESET, self.reset, eh.MODE_ONDOWN)
        ])
        self.event_handler = event_handler

        self.game = game
        self.FRAME = conf.FRAME
        self.bg_colour = (255, 255, 255)
        self.load(ID, definition)

    def load (self, ID = None, definition = None):
        # load a level
        self.ID = None if (ID is None or ID[0]) else str(ID[1])
        if ID is not None:
            # get data from file
            path = conf.LEVEL_DIR_CUSTOM if ID[0] else conf.LEVEL_DIR_MAIN
            with open(path + str(ID[1])) as f:
                definition = f.read()
        self.puzzle = Puzzle(self.game, definition, True, border = 1)
        self.players = [b for b in self.puzzle.blocks
                        if b.type == conf.B_PLAYER]
        self.dirty = True
        # store message
        if '@' in definition:
            d = definition
            d = d[d.find('@') + 1:]
            if '\n' in d:
                d = d[:d.find('\n')]
            self.msg = d.strip()
        else:
            self.msg = None
        self.winning = False

    def move (self, event, direction):
        # key callback to move player
        for player in self.players:
            player.add_force(direction, conf.FORCE_MOVE)

    def pause (self, event = None):
        self.game.start_backend(menu.PauseMenu)

    def reset (self, event = None):
        self.puzzle.init()
        self.players = [b for b in self.puzzle.blocks
                        if b.type == conf.B_PLAYER]

    def update (self):
        self.puzzle.step()
        # check for surfaces with their corresponding Block types on them
        win = True
        for col in self.puzzle.grid:
            for s, b in col:
                # goal surfaces have IDs starting at 0
                if s >= 0 and (not isinstance(b, Block) or s != b.type):
                    win = False
                    break
        # need to stay winning for one frame  - that is, blocks must have
        # stopped on the goals, not just be moving past them
        if win:
            if self.winning:
                # save to disk
                if self.ID is not None:
                    levels = conf.get('completed_levels', [])
                    if self.ID not in levels:
                        levels.append(self.ID)
                        conf.set('completed_levels', levels)
                        self.game.set_backend_attrs(menu.MainMenu, 're_init', True)
                self.game.quit_backend()
            else:
                self.winning = True
        else:
            self.winning = False

    def _mk_msg (self, screen, w, h):
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