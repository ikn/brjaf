import os

import pygame
from ext import evthandler as eh

import menu
from puzzle import Puzzle, BoringBlock
import level
import conf

# TODO:
# - save level message
# - mouse resize: change cursor while resizing to indicate allowed resize
#   directions (pygame.mouse.set_cursor)

class SolveMenu (menu.Menu):
    """The pause menu for solving a created level.

Takes the Level backend instance.

"""

    def init (self, level):
        menu.Menu.init(self, ((
            menu.Button('Continue', self.game.quit_backend),
            menu.Button('Reset', self._reset, level),
            menu.Button('Quit', self.game.quit_backend, 2)
        ),))

    def _reset (self, level):
        """Reset callback."""
        level.reset()
        self.game.quit_backend()

class DeleteMenu (menu.Menu):
    """Menu for deleting custom level saves.

Takes the level ID.

"""

    def init (self, ID, success_cb):
        self._default_selections[0] = (0, 2)
        menu.Menu.init(self, ((
                menu.Text('Delete?'),
                menu.Button('Yes', self._delete, ID, success_cb),
                menu.Button('No', self.game.quit_backend)
        ),))

    def _delete (self, ID, success_cb):
        """Delete the level with the given ID."""
        d = conf.LEVEL_DIR_CUSTOM if ID[0] == 1 else conf.LEVEL_DIR_DRAFT
        try:
            os.remove(d + ID[1])
        except OSError:
            pass
        self.game.quit_backend()
        self.game.set_backend_attrs(menu.MainMenu, 're_init', True)
        success_cb()

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

Further arguments: (directory, defn, fn = ''[, success_cb, *success_cb_args])

directory: directory to save in.
defn: level definition to save.
fn: text to initialise filename text entry with.
success_cb: a function to call with the filename the level is saved under on
            success.
success_cb_args: arguments to pass to success_cb after the filename.

"""

    def __init__ (self, *args, **kw):
        menu.Menu.__init__(self, *args, **kw)
        self._entry.toggle_focus()

    def init (self, directory, defn, fn = '', success_cb = None,
              *success_cb_args):
        if not fn:
            fn = ''
        # most bad characters will be caught when we try to create the file,
        # but space would create problems in listing the names, os.sep
        # would create files in directories if they exist, and : does weird
        # things without errors on Windows
        not_allowed = '/ ' + os.sep
        allowed = set(c for c in conf.PRINTABLE if c not in not_allowed)
        self._entry = menu.TextEntry(self, conf.LEVEL_NAME_LENGTH, fn, allowed)
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
                menu.Text('is blank'),
                menu.Button('Back', self.back)
            ), (
                menu.Text('Overwrite?'),
                menu.Button('Yes', self._save, True),
                menu.Button('No', self.back)
            ), (
                menu.Text('Invalid'),
                menu.Text('filename')
            ), (
                menu.Text('Can\'t write'),
                menu.Text('to that file')
            )
        ))

    def _save (self, overwrite = False):
        """Callback for trying to save using the entered name."""
        d = self.directory
        fn = self._entry.text
        if conf.PUZZLE_TEXT_UPPER:
            fn = fn.upper()
        # check for blank filename
        if fn == '':
            self.set_page(1)
            return
        # other filename validity checks that won't get caught when we try to
        # create the file:
        # - don't want to end up destroying parent/current directories
        # - Windows removes trailing spaces/dots
        if fn in ('.', '..') or (os.name == 'nt' and fn[-1] == '.'):
            self.set_page(3)
            return
        # confirm overwrite if exists (should cover case-insensitivity of
        # Windows filenames too)
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
        except OSError:
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
        if editor.state > 0:
            reset_data = (self.set_page, 1)
        else:
            reset_data = (self.game.quit_backend,)
        already_winning = 'The puzzle starts with the player already winning'
        no_player = 'There must be at least one player block'
        menu.Menu.init(self, (
            (
                menu.Button('Continue', self.game.quit_backend),
                menu.Button('Save', self._save),
                menu.Button('Save draft', self._save, True),
                menu.Button('Reset', *reset_data),
                menu.Button('Quit', self.game.quit_backend, 2)
            ), (
                menu.Text('Reset?'),
                menu.Button('Yes', self._reset),
                menu.Button('No', self.back)
            ), (
                menu.LongText(self, no_player, 11),
                menu.Button('Back', self.back)
            ), (
                menu.LongText(self, already_winning, 13),
                menu.Button('Back', self.back)
            ), (
                menu.Text('Level saved'),
                menu.Button('OK', self.back)
            )
        ))

    def _level_won (self):
        """Callback for solving the created level."""
        if hasattr(self, '_lvl'):
            self.game.quit_backend()
            # retrieve solution and add to definition
            self._defn += '\n: ' + self._lvl.stop_recording()
            del self._lvl
            d = conf.LEVEL_DIR_CUSTOM
        else:
            d = conf.LEVEL_DIR_DRAFT
        # ask for level name
        self.game.start_backend(SaveMenu, None, d, self._defn, self._editor.ID,
                                success_cb, self._editor)
        del self._defn

    def _save (self, draft = False):
        """Callback for 'save' option."""
        e = self._editor
        # try to save the current puzzle
        defn = e.editor.definition()
        if not draft:
            # check if there's a player block
            if not any(b.type == conf.B_PLAYER for b in e.editor.blocks):
                self.set_page(2)
                return
            # check if already winning
            if level.defn_wins(defn):
                self.set_page(3)
                return
        self._defn = defn
        self.game.quit_backend()
        if draft:
            # skip checks and solving
            self._level_won()
        else:
            # ask the player to solve the puzzle
            # show message making it clear what's going on
            defn += '\n@Solve the level first.'
            self._lvl = self.game.start_backend(level.LevelBackend, None, defn,
                                        SolveMenu, self._level_won)
            self._lvl.start_recording()

    def _reset (self):
        """Call back for 'reset' option."""
        self._editor._do_reset()
        self.game.quit_backend()


class Editor (object):
    """A puzzle editor (Game backend).

Takes arguments to pass to Editor.load.

    METHODS

load
change
resize
insert
delete
set_block
undo
redo
click_tile
switch_puzzle
reset
menu

    ATTRIBUTES

game: as given.
event_handler: as given.
ID: as given.
selector: puzzle used to select blocks/surfaces to add.
editor: the puzzle being edited.
puzzle: the current visible puzzle (editor or selector).
editing: whether the current puzzle is editor.
changes: a list of changes that have been made to the puzzle.
state: the current position in the changes list.

"""

    def __init__ (self, game, event_handler, ID = None, defn = None):
        self.game = game
        # add event handlers
        event_handler.add_event_handlers({
            pygame.MOUSEBUTTONDOWN: self._click,
            pygame.MOUSEBUTTONUP: self._unclick,
            pygame.MOUSEMOTION: lambda e: setattr(self, 'mouse_moved', True)
        })
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
            (conf.KEYS_MOVE_LEFT, [(self._move, (0,))]) + pzl_args,
            (conf.KEYS_MOVE_UP, [(self._move, (1,))]) + pzl_args,
            (conf.KEYS_MOVE_RIGHT, [(self._move, (2,))]) + pzl_args,
            (conf.KEYS_MOVE_DOWN, [(self._move, (3,))]) + pzl_args,
            (conf.KEYS_BACK, self.menu, od),
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

        self.FRAME = conf.FRAME
        self.load(ID, defn)

    def load (self, ID = None, defn = None):
        """Load a level.

load([ID][, defn])

ID: custom level ID.
defn: if ID is not given, load a level from this definition; if this is not
      given, load a blank level.

"""
        if ID is None:
            if defn is None:
                # blank grid
                defn = conf.BLANK_LEVEL
            self.ID = None
        else:
            # get data from file
            d = conf.LEVEL_DIR_DRAFT if ID[0] == 2 else conf.LEVEL_DIR_CUSTOM
            with open(d + ID[1]) as f:
                defn = f.read()
            self.ID = ID[1]
        if hasattr(self, 'editor'):
            self.editor.load(defn)
        else:
            self.editor = Puzzle(self.game, defn)
        self.editor.deselect()
        self.editor.select((0, 0))
        self.selector.deselect()
        self.selector.select((0, 0), True)
        self.puzzle = self.editor
        self.editing = True
        self.dirty = True
        self.changes = []
        self.state = 0
        self.mouse_moved = False
        self.resizing = False

    def change (self, *data):
        """Make a change to the puzzle; takes data to store in self.changes."""
        cs = self.changes
        # purge 'future' states
        cs = cs[:self.state]
        cs.append(data)
        # purge oldest state if need to (don't need to increment state, then)
        if len(cs) > conf.UNDO_LEVELS > 0:
            cs.pop(0)
        else:
            self.state += 1
        self.changes = cs

    def resize (self, amount, dirn):
        """Like Editor.editor.resize, but do some wrapper stuff."""
        lost = self.editor.resize(amount, dirn)
        # might not have changed
        if lost is not False:
            self.dirty = True
            self.change('resize', amount, dirn, lost)

    def _move (self, key, event, mods, direction):
        """Callback for arrow keys."""
        resize = False
        mods = (mods & pygame.KMOD_SHIFT, mods & pygame.KMOD_ALT)
        shrink = bool(mods[direction <= 1])
        grow = bool(mods[direction > 1])
        resize = shrink ^ grow
        if resize:
            # things could get messy if we're already mouse-resizing
            if not self.resizing:
                self.resize(1 if grow else -1, direction)
        else:
            # move selection
            self.puzzle.move_selected(direction)

    def insert (self):
        """Insert a block or surface at the current position."""
        if not self.editing:
            return
        # get type and ID of selected tile in selector puzzle
        col, row = self.selector.selected.keys()[0]
        x, y = self.editor.selected.keys()[0]
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
                old_b = current[1]
                b = self.editor.add_block((BoringBlock, ID), x, y)
                self.game.play_snd('place_block')
                self.change('set_block', old_b, b, x, y)
        else:
            if current[0] != ID:
                old_ID = current[0]
                self.editor.set_surface(x, y, ID)
                self.game.play_snd('place_surface')
                self.change('set_surface', old_ID, ID, x, y)

    def _insert_cb (self, *args):
        """Callback for conf.KEYS_INSERT."""
        if self.editing:
            self.insert()
        else:
            self.switch_puzzle()

    def delete (self, *args):
        """Delete a block or surface in the currently selected tile."""
        if self.editing:
            x, y = self.editor.selected.keys()[0]
            data = self.editor.grid[x][y]
            snd = True
            # delete block, if any
            if data[1] is not None:
                b = self.editor.rm_block(None, x, y)
                self.change('set_block', b, None, x, y)
            # set surface to blank if not already
            elif data[0] != conf.S_BLANK:
                s = self.editor.set_surface(x, y, conf.S_BLANK)
                self.change('set_surface', s, conf.S_BLANK, x, y)
            else:
                snd = False
            if snd:
                self.game.play_snd('delete')

    def set_block (self, b, x, y):
        """Add or remove a block to or from the puzzle.

set_block(b, x, y)

b: BoringBlock instance, or None to remove.
x, y: tile position.

"""
        if b is None:
            self.editor.rm_block(None, x, y)
        else:
            self.editor.add_block(b, x, y)

    def undo (self, *args):
        """Undo changes to the puzzle."""
        if self.state > 0:
            self.state -= 1
            # get change data
            data = self.changes[self.state]
            c, data = data[0], data[1:]
            # make the change to the puzzle
            if c == 'set_block':
                old_b, new_b, x, y = data
                self.set_block(old_b, x, y)
            elif c == 'set_surface':
                old, new, x, y = data
                self.editor.set_surface(x, y, old)
            elif c == 'resize':
                amount, direction, lost = data
                self.editor.resize(-amount, (direction - 2) % 4)
                # restore stuff that was lost in the resize
                for obj, x, y in lost:
                    if isinstance(obj, int):
                        self.editor.set_surface(x, y, obj)
                    else:
                        self.set_block(obj, x, y)
                self.dirty = True

    def redo (self, *args):
        """Redo undone changes."""
        if self.state < len(self.changes):
            # get change data
            data = self.changes[self.state]
            c, data = data[0], data[1:]
            self.state += 1
            # make the change to the puzzle
            if c == 'set_block':
                old_b, new_b, x, y = data
                self.set_block(new_b, x, y)
            elif c == 'set_surface':
                old, new, x, y = data
                self.editor.set_surface(x, y, new)
            elif c == 'resize':
                amount, direction, lost = data
                self.editor.resize(amount, direction)
                self.dirty = True

    def click_tile (self, insert, pos):
        """Insert or delete a block or surface at the given position.

click_tile(insert, pos)

insert: whether to insert the current block or surface (else delete).
pos: on-screen position to try to perform the action at.

"""
        # get clicked tile
        p = self.editor.point_tile(pos)
        if p:
            # clicked a tile in self.editor: switch to and select
            if not self.editing:
                self.switch_puzzle()
            self.editor.deselect()
            self.editor.select(p)
            (self.insert if insert else self.delete)()
        else:
            p = self.selector.point_tile(pos)
            if p:
                # clicked a tile in self.selector: switch to selector, then
                # select the tile
                if self.editing:
                    self.switch_puzzle()
                self.selector.deselect()
                self.selector.select(p)

    def _click (self, evt):
        """Handle mouse clicks."""
        button = evt.button
        pos = evt.pos
        if button in (1, 3):
            # left-click to insert, right-click to delete
            self.click_tile(button == 1, pos)
        elif button == 2:
            rel_pos = self.editor.point_pos(pos)
            # make sure we're clicking in the grid
            if rel_pos is None:
                return
            self._resize_sides = []
            # exclude a zone in the middle
            b = conf.RESIZE_DEAD_ZONE_BOUNDARY
            for i in (0, 1):
                if b < rel_pos[i] < 1 - b:
                    self._resize_sides.append(None)
                else:
                    # the axes we can resize on depends on where we start from
                    self._resize_sides.append(1 if rel_pos[i] > .5 else -1)
            if self._resize_sides == [None, None]:
                return
            self.resizing = list(pos)

    def _unclick (self, evt):
        """Handle mouse click release."""
        if evt.button == 2 and self.resizing:
            self.resizing = False
            del self._resize_sides

    def switch_puzzle (self, *args):
        """Switch selected puzzle between editor and block selector."""
        self.editing = not self.editing
        pzls = (self.editor, self.selector)
        if self.editing:
            new, old = pzls
        else:
            old, new = pzls
        # deselect old and select new
        for colour, pzl in enumerate((new, old)):
            pos = pzl.selected.keys()[0]
            pzl.deselect()
            pzl.select(pos, colour)
        self.puzzle = new

    def reset (self, *args):
        """Confirm resetting the puzzle."""
        if self.state > 0:
            self.game.start_backend(Menu, 1, self)
        # else nothing to reset

    def menu (self, *args):
        """Show the editor menu."""
        self.game.start_backend(Menu, 0, self)

    def _do_reset (self):
        """Actually reset the puzzle."""
        # just reset to original state - to whatever was loaded, if anything
        while self.state > 0:
            self.undo()

    def update (self):
        """Handle mouse movement."""
        if self.mouse_moved:
            pos = pygame.mouse.get_pos()
            if self.resizing:
                # change puzzle size if middle-click-dragging
                old_pos = self.resizing
                for i in (0, 1):
                    side = self._resize_sides[i]
                    if side is None:
                        # can't resize on this axis
                        continue
                    diff = pos[i] - old_pos[i]
                    threshold = min(conf.RESIZE_LENGTH * self.game.res[0],
                                    self.editor.tile_size(i))
                    while abs(diff) >= threshold:
                        # resize
                        sign = 1 if diff > 0 else -1
                        self.resize(sign * side, i + 2 * (sign == 1))
                        # prepare for resizing again
                        old_pos[i] += sign * threshold
                        diff -= sign * threshold
            else:
                # change selection based on mouse position
                # get tile under mouse
                tile = self.editor.point_tile(pos)
                if tile:
                    # editor: select tile under mouse
                    if not self.editing:
                        self.switch_puzzle()
                    self.editor.deselect()
                    self.editor.select(tile)
                else:
                    # selector: just make sure it's the current puzzle
                    tile = self.selector.point_tile(pos)
                    if tile:
                        if self.editing:
                            self.switch_puzzle()
            self.mouse_moved = False

    def draw (self, screen):
        """Draw the puzzles."""
        w, h = screen.get_size()
        w1 = int(conf.EDITOR_WIDTH * w)
        w2 = w - w1
        pad = int(conf.EDITOR_ARROW_PADDING * w)
        if self.dirty:
            screen.fill(conf.BG[conf.THEME])
            # get puzzle sizes
            e = self.editor.tiler
            s = self.selector.tiler
            if w1 != s.offset[0]:
                # screen size changed: need to change puzzle positions
                #e.offset = (pad, pad)
                s.offset = (w1, 0)
                s.reset()
        # draw puzzles
        drawn1 = self.editor.draw(screen, self.dirty, (w1, h))
                                  #(w1 - 2 * pad, h - 2 * pad))
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