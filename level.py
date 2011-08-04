import os
from math import ceil

import pygame
import evthandler as eh

import menu
from puzzle import Block, Puzzle
import conf

# TODO:
# - hint confirmation is something random (have criteria):
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

def get_levels (custom = False):
    """Get a list of existing levels.

Takes a boolean determining whether to load custom levels.

"""
    path = conf.LEVEL_DIR_CUSTOM if custom else conf.LEVEL_DIR_MAIN
    return sorted(f for f in os.listdir(path) if os.path.isfile(path + f))

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
        if level.solving:
            b = menu.Button('Stop solving', self._quit_then,
                            level.stop_solving)
        else:
            b = menu.Button('Help', self.set_page, 1)
        menu.Menu.init(self, (
            (
                menu.Button('Continue', self.game.quit_backend),
                b,
                menu.Button('Quit', self.game.quit_backend, 2)
            ),(
                menu.Text('Are you sure?'),
                menu.Button('Keep trying', self.game.quit_backend),
                menu.Button('Show me how', self._quit_then,
                            level.launch_solver)
            )
        ))

class SolnChooser (menu.Menu):
    """Show a menu to choose a solution number."""

    def init (self, cb, num_solns):
        # display as a grid: aim for w/h = sw/sh with n = cols*rows
        # using tiles for w, h, so get w = 2*cols+1, h = 2*rows+1
        # not perfect, but should look okay-ish in most cases
        sw, sh = self.game.screen.get_size()
        r = float(sw) / sh
        cols = (r - 1 + ((r - 1) ** 2 + 16 * num_solns * r) ** .5) / 4
        cols = int(round(cols))
        # create page
        page = [[] for i in xrange(cols)]
        # add buttons
        col = 0
        for i in xrange(num_solns):
            page[col].append(menu.Button(str(i + 1), self._quit_then, cb, i))
            col += 1
            col %= cols
        menu.Menu.init(self, (page,))


class Level (object):
    """A simple Puzzle wrapper to handle input and winning.

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
set_frozen
stop_solving
start_recording
stop_recording
update

    ATTRIBUTES

game: None.
ID: level ID; None if this is a custom level or a definition was given instead.
puzzle: puzzle.Puzzle instance.
players: player blocks in the puzzle.
msg: puzzle message.
solving: whether the puzzle is currently being solved.
solving_index: the current step in the solution being used to solve the puzzle.
recording: whether input is currently being recorded.
frozen: whether the solution being played back is paused.
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
            move = lambda d: [(self._move, (d,)), self._step_solution]
            freeze = lambda k, e, m: self.set_frozen()
            event_handler.add_key_handlers([
                (conf.KEYS_LEFT, [(self._move, (0,))]) + args,
                (conf.KEYS_UP, [(self._move, (1,))]) + args,
                (conf.KEYS_RIGHT, move(2)) + args,
                (conf.KEYS_DOWN, move(3)) + args,
                (conf.KEYS_RESET, self.reset, eh.MODE_ONDOWN),
                (conf.KEYS_TAB, self._fast_forward, eh.MODE_HELD),
                (conf.KEYS_NEXT, freeze, eh.MODE_ONDOWN),
                (conf.KEYS_RIGHT, self._step_solution) + args
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

        self._moved = []
        self._winning = False
        self.won = False
        self.solving = False
        self.solving_index = None
        self._ff = False
        self.recording = False
        self.frozen = False

    def move (self, *directions):
        """Apply force to all player blocks in the given directions."""
        # only make the move if haven't done already this frame
        directions = [d for d in directions if d not in self._moved]
        if not directions:
            return
        self._moved += directions
        if self.recording:
            self._record(directions)
        for d in set(directions):
            for player in self.players:
                player.add_force(d, conf.FORCE_MOVE)

    def _move (self, key, event, mods, direction):
        """Key callback to move player."""
        if not self.solving:
            self.move(direction)

    def reset (self, *args):
        """Reset the level to its state after the last call to Level.load."""
        if not self.solving:
            self.puzzle.init()
            self.players = [b for b in self.puzzle.blocks
                            if b.type == conf.B_PLAYER]
        # restart recording if want to
        if self.recording and self._blank_on_reset:
            self.start_recording()

    def _fast_forward (self, key, event, mods):
        """Key callback to fast-forward solving this frame."""
        if self.solving:
            # if holding ctrl, go even faster
            if pygame.KMOD_CTRL & mods:
                self._ff = 2
            else:
                self._ff = 1

    def _parse_soln (self, ID, speed = conf.SOLVE_SPEED):
        """Parse a solution string and return the result."""
        soln = self._solutions[ID]
        parsed = []
        for i, s in enumerate(soln.split(',')):
            s = s.strip()
            if i % 2:
                # directions
                s = [conf.SOLN_DIRS.index(c) for c in s]
            else:
                # time delay
                if s.startswith('['):
                    # got keys to hold for this waiting period
                    end = s.find(']')
                    hold = [conf.SOLN_DIRS.index(c) for c in s[1:end]]
                    s = s[end + 1:].strip()
                else:
                    hold = ()
                ops = ('>', '<')
                if any(op in s for op in ops):
                    # minimum and maximum values
                    allowed_range = [None, None]
                    while s:
                        # check for < and > being first
                        for op in ops:
                            if s.startswith(op):
                                s = s[1:].strip()
                                eq = s.startswith('=')
                                if eq:
                                    # remove = if found
                                    s = s[1:].strip()
                            else:
                                # op is not the first operator
                                continue
                            # the number is everything up to the next operator
                            next_op = len(s)
                            for o in ops:
                                j = s.find(o)
                                # or the end of the string
                                if j == -1:
                                    j = len(s)
                                next_op = min(j, next_op)
                            val = int(s[:next_op])
                            val = int(val)
                            # add/subtract one if >/<
                            val += (-1 if op == '<' else 1) * (1 - eq)
                            allowed_range[ops.index(op)] = val
                            s = s[next_op:].strip()
                    # constrain by given conditions
                    gt, lt = allowed_range
                    s = speed
                    if gt is not None:
                        s = max(s, gt)
                    if lt is not None:
                        s = min(s, lt)
                else:
                    s = int(s) if s else speed
                s = (hold, s)
            parsed.append(s)
        return parsed

    def solve (self, solution = 0):
        """Solve the puzzle.

Takes the solution number to use (its index in the list of solutions ordered as
in the puzzle definition).  This defaults to 0 (the 'primary' solution).

Returns a list of the directions moved.

This function is also called to move to the next step of an ongoing solution,
in which case it requires no argument.  In fact, if a solution is ongoing, it
cannot be called as detailed above (any argument is ignored).  This makes it
a bad idea to call this function while solving.

"""
        i = self.solving_index
        if i is None:
            # starting
            self.reset()
            self.solving = True
            self.solving_index = 0
            self._solution = self._parse_soln(solution)
            self._solution_ff = self._parse_soln(solution, 0)
            self._solve_time = self._solution[0][1]
            self._solve_time_ff = self._solution_ff[0][1]
            # call this function again to act on the first instruction
            move = self.solve()
        elif i == len(self._solution):
            # finished: just wait until the level ends
            move = []
        else:
            # continuing
            if i % 2:
                # make a move
                move = self._solution[i]
                self.move(*move)
                i += 1
                if i < len(self._solution):
                    self._solve_time = self._solution[i][1]
                    self._solve_time_ff = self._solution_ff[i][1]
                self.solving_index = i
            else:
                # wait
                # if fast-forwarding, use the quicker solution
                fast = self._ff or self.frozen
                t = self._solve_time_ff if fast else self._solve_time
                if t <= 0:
                    self.solving_index += 1
                    # do next step now
                    move = self.solve()
                else:
                    self._solve_time -= 1
                    self._solve_time_ff -= 1
                    held = self._solution[self.solving_index][0]
                    if held:
                        # want to send some input every frame for this delay
                        self.move(*held)
                        move = held
                    else:
                        move = []
        self._ff = False
        return move

    def set_frozen (self, frozen = None):
        """Set paused state of solution, or toggle without an argument."""
        if self.solving:
            self.frozen = not self.frozen if frozen is None else frozen

    def _step_solution (self, key, event, mods):
        """If paused, step the solution forwards once."""
        if self.solving and self.frozen:
            self._next_step = True

    def stop_solving (self):
        """Stop solving the puzzle."""
        self.solving = False
        self.solving_index = None
        self.frozen = False
        del self._solution, self._solution_ff, self._solve_time, \
            self._solve_time_ff, self._next_step
        if conf.RESET_ON_STOP_SOLVING:
            self.reset()

    def _record (self, directions):
        """Add input to the current recording."""
        directions = set(directions)
        recorded = self._recorded
        frame = self._recording_frame
        while len(recorded) < frame:
            # haven't added anything for some previous frames
            recorded.append(None)
        if len(recorded) == frame:
            # haven't added anything for this frame
            recorded.append(directions)
        else:
            # add more to this frame
            recorded[frame] |= directions
        self._recorded = recorded

    def start_recording (self, blank_on_reset = True):
        """Start recording input to the puzzle (moves).

Takes one boolean argument indicating whether to start recording again if the
puzzle is reset.  If already recording, calling this will delete the current
recording.

"""
        self.recording = True
        self._blank_on_reset = blank_on_reset
        self._recorded = []
        self._recording_frame = 0

    def stop_recording (self):
        """Stop recording input and return the recorded input.

The return value is in the standard solution format.  If not recording, this
function returns None.

"""
        result = ''
        t = 0
        for frame in self._recorded:
            if frame is None:
                # wait for a frame with input
                t += 1
            else:
                # add total wait time
                result += str(t) + ','
                t = 0
                # add input
                result += ''.join(conf.SOLN_DIRS[d] for d in frame) + ','
        self.recording = False
        del self._blank_on_reset, self._recorded, self._recording_frame
        return result[:-1]

    def update (self):
        """Update puzzle and check win conditions."""
        if not self.frozen or self._next_step:
            # fast-forward by increasing FPS
            if self.solving and self._ff == 2:
                if not hasattr(self, '_FRAME'):
                    self._FRAME = self.FRAME
                    self.FRAME /= conf.FF_SPEEDUP
            elif hasattr(self, '_FRAME'):
                self.FRAME = self._FRAME
                del self._FRAME
            # continue solving
            if self.solving:
                self.solve()
            # continue recording
            if self.recording:
                self._recording_frame += 1
            # step puzzle forwards
            self.puzzle.step()
            self._next_step = False
            # reset list of moves made this frame
            self._moved = []
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
            if not self._winning:
                self._winning = True
            # else if this is the first frame since we've won,
            elif not self.won:
                # clean up solution stuff in case this is to be reused
                if self.solving:
                    self.stop_solving()
                # save to disk
                elif self.ID is not None:
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


class LevelBackend (Level):
    """A Level subclass to handle drawing and make it a Game backend.

    CONSTRUCTOR

LevelBackend(game, event_handler[, ID][, definition],
             pause_menu = PauseMenu, win_cb = game.quit_backend)

pause_menu: menu.Menu subclass to start as a Game backend on pausing.  Its init
            method is passed this LevelBackend instance.

ID, definition and win_cb are as taken by Level.

    METHODS

pause
mk_msg
draw

    ATTRIBUTES

game: Game instance.
pause_menu: as given.

"""

    def __init__ (self, game, event_handler, ID = None, definition = None,
                  pause_menu = PauseMenu, win_cb = 'default'):
        self.game = game
        event_handler.add_key_handlers([
            (conf.KEYS_BACK, self.pause, eh.MODE_ONDOWN)
        ])
        self.event_handler = event_handler
        self.FRAME = conf.FRAME
        self.pause_menu = pause_menu
        if win_cb == 'default':
            win_cb = game.quit_backend
        Level.__init__(self, event_handler, ID, definition, win_cb)

    def load (self, *args, **kw):
        Level.load(self, *args, **kw)
        self.dirty = True
        self.msg_dirty = True
        self._first = True

    def reset (self, *args, **kw):
        if not self.solving:
            self._first = True
        Level.reset(self, *args, **kw)

    def launch_solver (self):
        """If more than one solution exists, ask which to use, then run it."""
        n = len(self._solutions)
        if n > 1:
            # show menu giving choice of solutions
            self.game.start_backend(SolnChooser, None, self.solve, n)
        else:
            # use only solution
            self.solve()

    def solve (self, *args, **kw):
        if self.solving_index is None:
            # starting solving: store old message
            self._msg = self.msg
        move = Level.solve(self, *args, **kw)
        if move:
            # show directions pressed in message
            self.msg = ''.join(conf.SOLN_DIRS_SHOWN[x] for x in move)
        else:
            # blank message (but still want it to take up a line)
            self.msg = ' '
        self.msg_dirty = True
        return move

    def stop_solving (self, *args, **kw):
        Level.stop_solving(self, *args, **kw)
        # restore message
        self.msg = self._msg
        self.msg_dirty = True

    def pause (self, *args):
        """Show the pause menu."""
        if self.pause_menu is not None:
            self.game.start_backend(self.pause_menu, None, self)

    def update (self, *args, **kw):
        # don't update on first frame in case stuff moves straight away (draw
        # first, so the initial level state can be seen)
        if self._first:
            self._first = False
            return
        Level.update(self, *args, **kw)

    def _mk_msg (self, screen):
        """Draw message to screen."""
        if not self.msg:
            self._msg_h = 0
            return
        # keep message size proportional to screen size (ss)
        w, h = screen.get_size()
        ss = min(w, h)
        font = [conf.MSG_FONT, int(round(ss * conf.MSG_LINE_HEIGHT)), False]
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
            msg_w, self._msg_h = msg.get_size()
            # centre message horizontally
            blit_x = (w - msg_w) / 2
            blit_y = int(round(h - self._msg_h - ss * conf.MSG_PADDING_BOTTOM))
            return msg, (blit_x, blit_y)
        else:
            # couldn't make font size small enough to fit the message on the
            # screen (_very_ unlikely): just don't display it
            self._msg_h = 0

    def draw (self, screen):
        """Draw the puzzle."""
        w, h = screen.get_size()
        # keep message size proportional to screen size (ss)
        ss = min(w, h)
        msg_rect = None
        if self.dirty:
            screen.fill(conf.BG)
        if self.dirty or self.msg_dirty:
            if not hasattr(self, '_msg_h'):
                # haven't generated message before
                self._msg_h = None
            if self._msg_h is None:
                msg_h = None
            else:
                # redrawing message: blank previous message area
                y = int(round(h - self._msg_h - ss * conf.MSG_PADDING_BOTTOM))
                msg_rect = (0, y, w, h - y)
                screen.fill(conf.BG, msg_rect)
                msg_h = self._msg_h
            # generate message, if any
            args = self._mk_msg(screen)
            if self._msg_h != msg_h:
                # message height changed: need to change puzzle area
                self.dirty = True
                screen.fill(conf.BG)
            # blit message to screen
            if args is not None:
                screen.blit(*args)
            self.msg_dirty = False
        if self.msg and self._msg_h:
            # reduce puzzle size to fit in message
            padding = ss * (conf.MSG_PADDING_TOP + conf.MSG_PADDING_BOTTOM)
            h -= self._msg_h + int(round(padding))
        drawn = self.puzzle.draw(screen, self.dirty, (w, h))
        if self.dirty:
            drawn = True
            self.dirty = False
        # need to update message area too (Puzzle.draw never returns True)
        elif msg_rect:
            if drawn:
                drawn.append(msg_rect)
            else:
                drawn = [msg_rect]
        return drawn