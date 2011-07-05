from math import ceil
from random import randrange, randint

import pygame
import evthandler as eh

from puzzle import Puzzle, BoringBlock
import conf

# TODO:
# document Menu and derivatives
# home/end keys
# scrollable element sets - set maximum number and scroll if exceed it
# u/d, l/r should go to prev/next col, row at ends: flatten elements to 1D list
# keys should select next option, like u/d, l/r: flatten with others removed
# options: key bindings/repeat rates
#          delete data (progress, custom levels, solution history)
#          appearance (select from multiple themes)
#          sound/music volume
# custom levels delete/rename/duplicate
# need another colour for special AND selected

# Text
# | Option
# | | Button
# | | | Entry (event:change)
# | | | | KeyEntry
# | | Select (abstract; .wrap; event:change; put arrows in edge blocks; text contains %x to replace with current value)
# | | | DiscreteSelect (.options)
# | | | RangeSelect (.min, .max, .step)
# | | | | FloatSelect (.dp)
# Image (.w, .h, .img, .border = (size, colour))

class Text:
    """A simple widget to display (immutable) text.

    CONSTRUCTOR

Text(text)

text: the text to display.

    ATTRIBUTES

text: the widget's text.
size: the length of the text.
selectable: whether the widget can be selected (always False).
special: whether the text is displayed in a different style; defaults to False.
         Call update after changing to redraw.
pos: the position of the first character in the grid display, or None if
     unknown.
menu: the Menu instance the widget exists in, or None if unknown.
puzzle: the Puzzle instance the widget exists in, or None if unknown.

"""

    def __init__ (self, text, special = False):
        self.text = u''
        self._append(text)
        self.size = len(self.text)
        self.selectable = False
        self.pos = None
        if not hasattr(self, 'menu'):
            self.menu = None
        if not hasattr(self, 'puzzle'):
            self.puzzle = None
        self.special = False

    def __str__ (self):
        text = self.text.encode('utf-8')
        return '<{0}: \'{1}\'>'.format(self.__class__.__name__, text)

    __repr__ = __str__

    def _append (self, text):
        """Append a string to the end of the text, properly."""
        if not isinstance(text, unicode):
            text = text.decode('utf-8')
        chars = []
        for c in text:
            o = ord(c)
            if o >= conf.MIN_CHAR_ID and o <= conf.MAX_CHAR_ID:
                chars.append(c)
            else:
                chars.append(u' ')
        self.text += ''.join(chars)

    def update (self):
        """Make any colour changes (selected, special) visible."""
        # move blocks
        change = set()
        pos = list(self.pos)
        for dx in xrange(self.size):
            change.add(tuple(pos))
            ID = ord(self.text[dx])
            if self.selected:
                ID += conf.SELECTED_CHAR_ID_OFFSET
            elif self.special:
                ID += conf.SPECIAL_CHAR_ID_OFFSET
            self.puzzle.grid[pos[0]][pos[1]][1].type = ID
            pos[0] += 1
        self.puzzle.tiler.change(*change)

class Option (Text):
    """A selectable widget.  Inherits from Text.

    METHODS

attach_event
set_selected

    ATTRIBUTES

selectable: always True.
selected: whether this widget is currently selected.
ehs: an event: handlers dict of attached event handlers.

    EVENTS

SELECT_EVENT: the selected state has changed.  This is called after the
              selected attribute is changed to the new state.

"""

    def __init__ (self, text):
        Text.__init__(self, text)
        self.selectable = True
        self.selected = False
        self.ehs = {}

    SELECT_EVENT = 0

    def _throw_event (self, event):
        """Call the handlers attached to the given event ID."""
        if event in self.ehs:
            for handler, args in self.ehs[event]:
                handler(*args)

    def attach_event (self, event, handler, args = ()):
        """Attach a handler to an event.

attach_event(event, handler, args = ())

event: the event ID to run the handler for.
handler: a function to call when the event is thrown.
args: arguments to pass to the handler; no other arguments are passed.

"""
        data = (handler, args)
        try:
            self.ehs[event].append(data)
        except KeyError:
            self.ehs[event] = [data]

    def set_selected (self, selected):
        """Set the widget's selected state."""
        if selected == self.selected:
            return
        self.selected = selected
        self.update()
        self._throw_event(Option.SELECT_EVENT)

class Button (Option):
    """A button widget.  Inherits from Option.

    CONSTRUCTOR

Button(text[, click_handler, *click_args])

Passing click_handler and click_args is identical to calling
Button.attach_event(Button.CLICK_EVENT, click_handler, click_args).

    METHODS

click

    EVENTS

CLICK_EVENT: the button was clicked.

"""

    def __init__ (self, text, click_handler = None, *click_args):
        Option.__init__(self, text)
        if click_handler is not None:
            self.attach_event(Button.CLICK_EVENT, click_handler, click_args)

    CLICK_EVENT = 1

    def click (self):
        """Trigger handlers attached to CLICK_EVENT."""
        self._throw_event(Button.CLICK_EVENT)

class Entry (Button):
    """A fixed-size text entry widget.  Inherits from Button.

    CONSTRUCTOR

Entry(menu, max_size, initial_text = '', allowed = conf.PRINTABLE)

menu: the Menu instance this widget is attached to.
max_size: maximum number of characters the entry can hold.
initial_text: text to start with; gets truncated to max_size.
allowed: list/string of allowed characters (initial_text is not checked for
         compliance).

    EVENTS

CHANGE_EVENT: the text in the entry changed.

"""

    def __init__ (self, menu, max_size, initial_text = '', allowed = conf.PRINTABLE):
        Button.__init__(self, initial_text[:max_size], self.toggle_focus)
        self.menu = menu
        self.max_size = max_size
        self.focused = False
        self.allowed = set(allowed)
        self._toggle_keys = set(conf.KEYS_NEXT + (pygame.K_ESCAPE,))

    def toggle_focus (self):
        """Toggle whether the entry is focused.

When a widget is focused, it catches keypresses and its text can be edited.
Only one widget can be focused at a time, for which reason it may not be
possible to toggle focus; the return value indicates whether it was possible.

"""
        if self.focused:
            self.focused = False
            err = 'something else captured input while {0} had it'.format(self)
            assert self.menu.release_input(self), err
        else:
            captured = self.menu.capture_input(self)
            if captured:
                self.focused = True
            return captured

    def input (self, event):
        """Takes a keypress event to alter the entry's text."""
        k = event.key
        u = event.unicode
        if k in self._toggle_keys:
            self.toggle_focus()
        elif u:
            text = self.text
            if k == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif k == pygame.K_DELETE:
                pass
            elif u in self.allowed and self.size != self.max_size:
                self._append(u)
            if text != self.text:
                self.size = len(self.text)
                self.menu.refresh_text()

class Select (Option):
    pass

class Image:
    pass

class Menu:
    def __init__ (self, game, event_handler, *extra_args):
        event_handler.add_event_handlers({pygame.KEYDOWN: self._access_keys})
        args = (
            eh.MODE_ONDOWN_REPEAT,
            max(int(conf.MENU_INITIAL_DELAY * conf.MENU_FPS), 1),
            max(int(conf.MENU_REPEAT_DELAY * conf.MENU_FPS), 1)
        )
        event_handler.add_key_handlers([
            (conf.KEYS_UP, [(self.move_selection, (-1,))]) + args,
            (conf.KEYS_DOWN, [(self.move_selection, (1,))]) + args,
            (conf.KEYS_LEFT, [(self.alter, (-1,))]) + args,
            (conf.KEYS_RIGHT, [(self.alter, (1,))]) + args,
            (conf.KEYS_NEXT, self.select, eh.MODE_ONDOWN),
            (conf.KEYS_BACK, self.back, eh.MODE_ONDOWN)
        ])
        self.event_handler = event_handler
        self.game = game
        self.FRAME = conf.MENU_FRAME
        self.last_pages = []
        self.captured = False
        self.init(*extra_args)
        self.set_page(0)

    def init (self, pages):
        self.pages = []
        for page in pages:
            if isinstance(page[0], (Text, Image)):
                # one column
                page = [page]
            page = [col for col in page if col]
            self.pages.append(page)
        self.re_init = False
        self.dirty = True
        self.sel = None
        self.page_ID = None
        self.page = None
        self.definition = None

        # get maximum page width and height
        self.w, self.h = (max(self.page_dim(page)[i] for page in self.pages)
                          for i in xrange(2))
        # create grid
        self.grid_w = max(self.w, int(ceil(self.h * conf.MAX_RATIO)))
        self.grid_h = max(self.h, int(ceil(self.w * conf.MAX_RATIO)))
        if self.grid_w % 2 != self.w % 2:
            self.grid_w += 1
        if self.grid_h % 2 != self.h % 2:
            self.grid_h += 1
        self.grids = {}

    def page_dim (self, page, padding = True):
        if padding:
            return (sum(max(text.size + 1 for text in c) for c in page) + 1,
                    2 * max(len(c) for c in page) + 1)
        else:
            return (len(page), max(len(c) for c in page))

    def set_page (self, page):
        # change the current menu page and its associated elements
        if page == self.page_ID:
            return
        select = None
        if page == -1:
            # return to last page
            try:
                page, select = self.last_pages.pop()
            except IndexError:
                # no last page (this is the root page)
                self.game.quit_backend()
                return
        elif self.page_ID is not None:
            # save current selection
            self.last_pages.append((self.page_ID, self.sel))
        # clear selection on current page
        self.set_selected(None)
        # create grid if need to
        self.page_ID = page
        self.page = self.pages[self.page_ID]
        try:
            self.grid = self.grids[page]
        except KeyError:
            self.generate_grid()
            self.grids[self.page_ID] = self.grid
        # compile options' first letters for access keys
        self.keys = {}
        for i, col in enumerate(self.page):
            for j, element in enumerate(col):
                if isinstance(element, Option):
                    # ignore caps - add for each variation
                    c = element.text[0]
                    ks = set((c, c.lower(), c.upper()))
                    for k in ks:
                        try:
                            self.keys[k].append((i, j))
                        except KeyError:
                            self.keys[k] = [(i, j)]
        # set selection
        if select is None:
            # select first selectable option if possible
            select = [0, 0]
        self.set_selected(select)
        self.dirty = True

    def refresh_text (self, page_ID = None):
        # redraw text for the given page ID, or the current page
        if page_ID is None:
            page_ID = self.page_ID
            page = self.page
        else:
            page = self.pages[page_ID]
        change = set()
        # update both old and new sets of covered tiles
        puzzle = self.grids[page_ID]
        rm_w = self._prev_dim[0]
        rm_x0 = (self.grid_w - rm_w) / 2 + 1
        add_w, h = self.page_dim(page)
        add_x0 = (self.grid_w - add_w) / 2 + 1
        x0 = min(rm_x0, add_x0)
        y0 = (self.grid_h - h) / 2 + 1
        w = max(rm_w + rm_x0 - x0, add_w + add_x0 - x0)
        for rm in (True, False):
            for col in page:
                for y, text in enumerate(col):
                    y = y0 + 2 * y
                    if rm:
                        # remove letters
                        for x in xrange(w):
                            x += x0
                            b = puzzle.grid[x][y][1]
                            if b is not None and b.type > conf.MAX_ID:
                                puzzle.rm_block(None, x, y)
                            # replace with original random block, if any
                            try:
                                b = (BoringBlock, self.definition[1][(x, y)])
                            except KeyError:
                                pass
                            else:
                                puzzle.add_block(b, x, y)
                    else:
                        # add letters back
                        text.pos = (add_x0, y)
                        for x, c in enumerate(text.text):
                            o = ord(c)
                            if text.special:
                                o += conf.SPECIAL_CHAR_ID_OFFSET
                            puzzle.add_block((BoringBlock, o), add_x0 + x, y)
                x0 += max(0, *(text.size + 1 for text in col))
        # reapply selection
        self.set_selected(self.sel, True)

    def generate_grid (self):
        # generate a grid containing random stuff and this page's text
        if self.definition is None:
            # create definition for random surfaces and blocks
            definition = ['{0} {1}\n'.format(self.grid_w, self.grid_h)]
            for min_ID, rand_ratio in ((0, conf.RAND_B_RATIO),
                                       (conf.MIN_ID, conf.RAND_S_RATIO)):
                things = {} # blocks or surfaces depending on the iteration
                i = 0
                n = int(min(rand_ratio, 1) * self.grid_w * self.grid_h)
                n = min(n, n - len(things))
                while i < n:
                    pos = (randrange(self.grid_w), randrange(self.grid_h))
                    type_ID = randint(min_ID, conf.MAX_ID)
                    if pos not in things:
                        things[pos] = type_ID
                        i += 1
                definition.append(things)
            self.definition = definition
        else:
            definition = self.definition
        things = dict(definition[1])
        # letters count as blocks; add to the right part of the definition
        self._prev_dim = (w, h) = self.page_dim(self.page)
        x0 = (self.grid_w - w) / 2 + 1
        y0 = (self.grid_h - h) / 2 + 1
        for col in self.page:
            for y, text in enumerate(col):
                text.pos = (x0, y0 + 2 * y)
                for x, c in enumerate(text.text):
                    # just replace any blocks that might be here already
                    o = ord(c)
                    if text.special:
                        o += conf.SPECIAL_CHAR_ID_OFFSET
                    things[(x0 + x, y0 + 2 * y)] = o
            x0 += max(0, *(text.size + 1 for text in col))
        # generate expected format definition
        definition = definition[0] + '\n\n'.join(
            '\n'.join(
                '{0} {1} {2}'.format(type_ID, *pos)
                for pos, type_ID in things.iteritems()
            ) for things in (things, definition[2])
        )
        self.grid = Puzzle(self.game, definition, False, overflow = 'grow')
        # Texts need a reference to Tiler to change their appearance
        for col in self.page:
            for text in col:
                text.puzzle = self.grid

    def selected (self, sel = None):
        if sel is None:
            sel = self.sel
        try:
            return self.page[sel[0]][sel[1]]
        except IndexError:
            return None

    def set_selected (self, sel, force = False):
        # set the currently selected option
        if sel is not None:
            sel = list(sel)
        if sel != self.sel or force:
            if self.sel is not None:
                # deselect current option
                self.selected().set_selected(False)
            if sel is not None:
                # select new option
                option = self.selected(sel)
                if not option.selectable:
                    # select next selectable element if possible
                    # get list of selectable elements
                    selectable = []
                    for i in xrange(len(self.page)):
                        for j in xrange(len(self.page[i])):
                            element = self.page[i][j]
                            if isinstance(element, Option):
                                selectable.append([i, j])
                    if selectable:
                        # check if any elements before the end are selectable
                        following = [x for x in selectable if x > sel]
                        if following:
                            sel = min(following)
                        else:
                            sel = min(selectable)
                    else:
                        sel = None
                if sel is not None:
                    self.selected(sel).set_selected(True)
            self.sel = sel

    def move_selection (self, key, event, mods, amount, axis = 1):
        # change the selected option
        if self.sel is None:
            return
        sel = self.sel[:]
        direction = 1 if amount > 0 else -1
        if axis == 0:
            num_elements = len(self.page)
        else:
            num_elements = max(len(col) for col in self.page)
        while amount:
            sel[axis] += amount
            sel[axis] %= num_elements
            selected = self.selected(sel)
            # skip non-existent and non-selectable elements
            while selected is None or not selected.selectable:
                sel[axis] += amount
                sel[axis] %= num_elements
                selected = self.selected(sel)
            amount -= direction
        # change selection
        self.set_selected(sel)

    def alter (self, key, event, mods, amount):
        if self.sel is None:
            return
        element = self.page[self.sel[0]][self.sel[1]]
        if not isinstance(element, Select):
            self.move_selection(None, None, None, amount, 0)
            return
        # TODO: alter

    def select (self, *args):
        # choose the currently selected option, if any
        if self.sel is None:
            return
        option = self.page[self.sel[0]][self.sel[1]]
        if hasattr(option, 'click'):
            option.click()

    def back (self, *args):
        # go back one page, if possible
        self.set_page(-1)

    def _access_keys (self, event):
        if self.captured:
            # pass input to capture function
            self.captured.input(event)
            return
        # select options by pressing their first letter
        try:
            elements = self.keys[event.unicode]
        except KeyError:
            # no matches
            return
        if len(elements) == 1:
            # one match: select it and try to click it
            self.set_selected(elements[0])
            self.select()
        else:
            # multiple matches: select next one
            x, y = self.sel
            w, h = self.page_dim(self.page, False)
            sel = min(((j - y) % h, (i - x) % w, i, j)
                    for i, j in elements if i != x or j != y)[2:]
            self.set_selected(sel)

    def capture_input (self, element):
        """Capture all keyboard input.

Takes an element to pass all keypress events to the input method of.  Returns
whether the capture was allowed.

"""
        if self.captured:
            return False
        else:
            self.event_handler.keys_active = False
            self.captured = element
            return True

    def release_input (self, element):
        """Undo the capture set up through Menu.capture_input.

Takes the same element as was used to capture input; if this does not match, no
change is made.  Returns whether input was released (or was never captured
to start with).

"""
        if element is self.captured:
            self.event_handler.keys_active = True
            self.captured = False
            return True
        elif self.captured:
            return False
        else:
            return True

    def update (self):
        if self.re_init:
            # pages might have changed
            ID = self.page_ID
            selected = self.sel[:]
            self.init()
            self.set_page(ID)
            self.set_selected(selected)

    def draw (self, screen):
        if self.dirty:
            # make sure the options fit nicely on the screen in both dimensions
            res = self.game.res
            tile_size = min(float(res[0]) / self.w, float(res[1]) / self.h)
            grid_w = int(tile_size * self.grid_w)
            grid_h = int(tile_size * self.grid_h)
            self.grid.tiler.mode = ('grid', grid_w, grid_h)
        drawn = self.grid.draw(screen, self.dirty)
        self.dirty = False
        return drawn

import level
import editor

class MainMenu (Menu):
    """The game's main menu."""

    def init (self):
        pages = (
            (
                Button('Play', self.set_page, 1),
                Button('Custom', self.set_page, 2),
                Button('Options', self.set_page, 5)
            ), [], (
                Button('New', self.game.start_backend, editor.Editor),
                Button('Load', self.set_page, 3)
            ), [], (
                Button('Play', self._with_custom_lvl, level.Level),
                Button('Edit', self._with_custom_lvl, editor.Editor),
                #Button('Delete'),
                #Button('Rename'),
                #Button('Duplicate')
            ), (
                Button('Input', self.set_page, 6),
                Button('Sound', self.set_page, 7)
            ), (
                Text('Key repeat'),
                Option('Delay 0.2'), # 0.1 - 1.0 | FloatSelect('Delay %x', .1, 1, .1)
                Option('Speed 10'), # 1 - 10 | RangeSelect('Speed %x', 1, 10, 1) | is 1 / repeat_delay
                Button('Save', self.back)
            ), (
                Text('Volume'),
                Option('Music 50'),
                Option('Sound 50'),
                Button('Save', self.back)
            )
        )

        # create level pages
        for page, custom in ((1, False), (3, True)):
            lvls = level.get_levels(custom)
            page = pages[page]
            if not lvls:
                # nothing to show
                page.append(Text('Empty'))
                continue
            if not custom:
                completed = conf.get('completed_levels', [])
                uncompleted_to_show = conf.NUM_UNCOMPLETED_LEVELS
            # create columns
            col = 0
            for i in xrange(conf.LEVEL_SELECT_COLS):
                page.append([])
            # add buttons
            for lvl in lvls:
                lvl = str(lvl)
                ID = (custom, lvl)
                if custom:
                    b = Button(lvl, self._custom_lvl_cb, ID)
                else:
                    b = Button(lvl, self.game.start_backend, level.Level, ID)
                page[col].append(b)
                if not custom:
                    # highlight completed levels
                    if lvl in completed:
                        b.special = True
                    else:
                        # only show a few unfinished levels
                        uncompleted_to_show -= 1
                        if uncompleted_to_show == 0:
                            # only show a certain number of uncompleted levels
                            break
                col += 1
                col %= conf.LEVEL_SELECT_COLS

        Menu.init(self, pages)

    def _custom_lvl_cb (self, ID):
        """Set up page shown on selecting a custom level."""
        self._custom_lvl_ID = ID
        self.set_page(4)

    def _with_custom_lvl (self, obj):
        """Call function or start backend with self._custom_lvl_ID."""
        if hasattr(obj, '__call__'):
            # function; give level to it
            obj(self._custom_lvl_ID)
        else:
            # backend class: start backend
            self.game.start_backend(obj, self._custom_lvl_ID)