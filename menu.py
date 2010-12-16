from math import ceil
from random import randrange, randint

import evthandler as eh

import level
from puzzle import Puzzle

import conf

# TODO:
# document Menu and derivatives
# select options by first letter
# text placement needs fixing for smaller pages (centre on both axes)
# scrollable element sets - set maximum number and scroll if exceed it

# Text (.size, .text)
# | Option (.attach(event, handler))
# | | Button (.select; event:select)
# | | Select (abstract; .wrap; event:change; put arrows in edge blocks; text contains %x to replace with current value)
# | | | DiscreteSelect (.options)
# | | | RangeSelect (.min, .max, .step)
# | | | | FloatSelect (.dp)
# | | Entry (event:change)
# | | | KeyEntry
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
pos: the position of the first character in the grid display, or None if
     unknown.
puzzle: the Puzzle instance the widget exists in, or None if unknown.

"""

    def __str__ (self):
        return '<{0}: \'{1}\'>'.format(self.__class__.__name__, self.text)

    __repr__ = __str__

    def __init__ (self, text):
        chars = []
        for c in text:
            if ord(c) >= conf.MIN_CHAR_ID and ord(c) <= conf.MAX_CHAR_ID:
                chars.append(c)
            else:
                chars.append(' ')
        self.text = ''.join(chars)
        self.size = len(self.text)
        self.selectable = False
        self.pos = None
        self.puzzle = None

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
        # move blocks
        change = set()
        pos = list(self.pos)
        for dx in xrange(self.size):
            change.add(tuple(pos))
            ID = ord(self.text[dx]) + conf.SELECTED_CHAR_ID_OFFSET * selected
            self.puzzle.grid[pos[0]][pos[1]][1].type = ID
            pos[0] += 1
        self.puzzle.tiler.change(*change)
        self.selected = selected
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

class Menu:
    def __init__ (self, game, event_handler):
        args = (
            eh.MODE_ONDOWN_REPEAT,
            max(int(conf.MENU_INITIAL_DELAY * conf.MENU_FPS), 1),
            max(int(conf.MENU_REPEAT_DELAY * conf.MENU_FPS), 1)
        )
        event_handler.add_key_handlers([
            (conf.KEYS_LEFT, [(self.alter, (-1,))]) + args,
            (conf.KEYS_UP, [(self.move_selection, (-1,))]) + args,
            (conf.KEYS_RIGHT, [(self.alter, (1,))]) + args,
            (conf.KEYS_DOWN, [(self.move_selection, (1,))]) + args,
            (conf.KEYS_BACK, self.back, eh.MODE_ONDOWN),
            (conf.KEYS_NEXT, self.select, eh.MODE_ONDOWN)
        ])
        self.event_handler = event_handler
        self.game = game
        self.FRAME = conf.MENU_FRAME
        self.last_pages = []
        self.init()
        self.set_page(0)

    def init (self, pages):
        self.pages = pages
        self.re_init = False
        self.dirty = True
        self.selected = None
        self.page_ID = None
        self.page = None
        self.definition = None

        # get maximum page width and height
        w = 0
        h = 0
        for page in self.pages:
            w = max(w, max(text.size for text in page))
            h = max(h, len(page))
        # add padding
        self.w = w + 2
        self.h = 2 * h + 1
        # create grid
        self.grid_w = max(self.w, int(ceil(self.h * conf.MAX_RATIO)))
        self.grid_h = max(self.h, int(ceil(self.w * conf.MAX_RATIO)))
        if self.grid_w % 2 != self.w % 2:
            self.grid_w += 1
        if self.grid_h % 2 != self.h % 2:
            self.grid_h += 1
        self.grids = {}

    def set_page (self, page):
        if self.re_init:
            # pages might have changed
            self.init()
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
            self.last_pages.append((self.page_ID, self.selected))
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
        # set selection
        if select is None:
            # select first selectable option if possible
            selectable = [t for t in self.page if isinstance(t, Option)]
            if selectable:
                select = self.page.index(selectable[0])
        self.set_selected(select)
        self.dirty = True

    def generate_grid (self):
        # generate a grid containing random stuff and this page's text
        if self.definition is None:
            # create definition for random surfaces and blocks
            definition = ['{0} {1}\n'.format(self.grid_w, self.grid_h)]
            data = ((0, conf.RAND_B_RATIO), (conf.MIN_ID, conf.RAND_S_RATIO))
            for min_ID, rand_ratio in data:
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
        x0 = (self.grid_w - self.w) / 2 + 1
        y0 = (self.grid_h - self.h) / 2 + 1
        for y, text in enumerate(self.page):
            text.pos = (x0, y0 + 2 * y)
            for x, c in enumerate(text.text):
                # just replace any blocks that might be here already
                things[(x0 + x, y0 + 2 * y)] = ord(c)
        # generate expected format definition
        definition = definition[0] + '\n\n'.join(
            '\n'.join(
                '{0} {1} {2}'.format(type_ID, *pos)
                for pos, type_ID in things.iteritems()
            ) for things in (things, definition[2])
        )
        self.grid = Puzzle(self.game, definition, False, overflow = 'grow')
        # Texts need a reference to Tiler to change their appearance
        for text in self.page:
            text.puzzle = self.grid

    def set_selected (self, selected):
        # set the currently selected option
        if selected != self.selected:
            if self.selected is not None:
                # deselect current option
                self.page[self.selected].set_selected(False)
            if selected is not None:
                # select new option
                option = self.page[selected]
                if not option.selectable:
                    # select next selectable option if possible
                    selectable = [t for t in self.page if isinstance(t, Option)]
                    if selectable:
                        index = selectable.index(min(selectable))
                        selected = self.page.index(selectable[index])
                    else:
                        selected = None
                if selected is not None:
                    self.page[selected].set_selected(True)
            self.selected = selected

    def move_selection (self, event, amount):
        # change the selected option
        if self.selected is None:
            return
        selected = self.selected
        direction = 1 if amount > 0 else -1
        num_elements = len(self.page)
        while amount:
            selected += amount
            selected %= num_elements
            # skip non-selectable elements
            while not self.page[selected].selectable:
                selected += amount
                selected %= num_elements
            amount -= direction
        # change selection
        self.set_selected(selected)

    def alter (self, event, amount):
        if self.selected is None:
            return

    def back (self, event = None):
        # go back one page, if possible
        self.re_init = True
        self.set_page(-1)

    def select (self, event = None):
        # choose the currently selected option, if any
        if self.selected is None:
            return
        option = self.page[self.selected]
        if hasattr(option, 'click'):
            option.click()

    def update (self):
        pass

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

class MainMenu (Menu):
    def init (self):
        try:
            self.n += 1
        except AttributeError:
            self.n = 0
        Menu.init(self, ((Text('test'),) * self.n +
            (
                Button('Play', self.game.start_backend, level.Level, 1),
                Button('Options', self.set_page, 2),
                Button('Quit', self.game.quit_backend)
            ), (
                Text('Title'),
                Option('What')
            ), (
                Button('Input', self.set_page, 3),
                Button('Sound', self.set_page, 4)
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
        ))

class PauseMenu (Menu):
    def init (self):
        Menu.init(self, (
            (
                Button('Continue', self.game.quit_backend),
                Button('Hint', self.set_page, 1),
                Button('Quit', self.game.quit_backend, 2)
            ),
        ))