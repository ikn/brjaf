from os.path import exists

import pygame

from tiler import Tiler, draw_rect
import conf

# TODO:
# document
# bouncing blocks
# block orientation - set after motion, use in draw_tile
# crop characters to fit in tiles

def autocrop (s):
    """Return the smallest rect containing all non-transparent pixels.

Returns False if the image is completely transparent.

"""
    alpha = pygame.surfarray.array_alpha(s)
    alpha = (alpha, alpha.T)
    w, h = s.get_size()
    borders = []
    for i, pos in enumerate((0, 0, w - 1, h - 1)):
        axis = i % 2
        diff = -1 if i > 1 else 1
        try:
            while not any(alpha[axis][pos]):
                pos += diff
        except IndexError:
            # went out of array bounds, so the whole image is transparent
            return False
        borders.append(pos + (i > 1))
    b = borders
    return (b[0], b[1], b[2] - b[0], b[3] - b[1])

def is_immoveable (tile):
    if isinstance(tile, Block):
        surface = tile.puzzle.grid[tile.pos[0]][tile.pos[1]][0]
        # immoveable blocks can be moved on slippery surfaces
        immoveable = tile.type == conf.B_IMMOVEABLE and surface != conf.S_SLIDE
    else:
        immoveable = False
    return tile == conf.WALL or immoveable

def force_dir (axis, force):
    return axis + (2 if force > 0 else 0)

def force_axis (direction, force):
    axis = direction % 2
    force = (1 if direction > 1 else -1) * force
    return axis, force

def opposite_dir (direction):
    return (direction + 2) % 4

class BoringBlock (object):
    def __init__ (self, type_ID, puzzle, pos, orientation = None):
        self.type = type_ID
        self.pos = list(pos)
        self.dir = orientation

    def __str__ (self):
        return '<block: {0} at {1}>'.format(self.type, self.pos)

    __repr__ = __str__

class Block (BoringBlock):
    def __init__ (self, type_ID, puzzle, pos, orientation = None):
        BoringBlock.__init__ (self, type_ID, puzzle, pos, orientation)
        self.puzzle = puzzle
        self.reset()

    def reset (self, keep_resultant = False):
        # reset some stuff to get ready for the next step
        if keep_resultant:
            resultant = self.resultant()
            self.sources = [{None: resultant[axis]} for axis in (0, 1)]
            self.handled = False
        else:
            self.sources = [{}, {}]
            self.handled = True
        self.targets = [{}, {}]
        self.unhandled_targets = [[], []]
        self.forces = [[], []]

    def resultant (self):
        # calculate resultant force on each axis
        return [sum(self.sources[axis].values()) for axis in (0, 1)]

    def add_force (self, direction, force):
        # wrapper for adding non-Block force sources
        axis, force = force_axis(direction, force)
        self.add_sources(axis, {None: force})

    def add_sources (self, axis, sources):
        if conf.DEBUG:
            print 'add_sources', self, axis, sources
        # None means not from a block; might be more than one
        if sources:
            try:
                self.sources[axis][None] += sources[None]
            except KeyError:
                pass
            else:
                del sources[None]
            self.sources[axis].update(sources)
            self.handled = False

    def rm_sources (self, axis, *sources):
        if conf.DEBUG:
            print 'rm_sources', self, axis, sources
        if sources:
            for source in sources:
                try:
                    del self.sources[axis][source]
                except KeyError:
                    pass
            self.handled = False

    def add_targets (self, axis, *targets):
        if conf.DEBUG:
            print 'add_targets', self, axis, targets
        if targets:
            u = self.unhandled_targets[axis]
            new = [t for t in targets if t not in u]
            if new:
                u += new
                self.handled = False

    def rm_targets (self, axis, *targets):
        if conf.DEBUG:
            print 'rm_targets', self, axis, targets
        if targets:
            for target in targets:
                try:
                    del self.targets[axis][target]
                except KeyError:
                    # not handled yet
                    u = self.unhandled_targets[axis]
                    if target in u:
                        u.remove(target)
                try:
                    target.rm_sources(axis, self)
                except AttributeError:
                    pass
            self.handled = False

    def target_tile (self, resultant = None):
        # get target tile for a given (or the current) resultant force
        if resultant is None:
            resultant = self.resultant()
        pos = self.pos[:]
        for axis in (0, 1):
            if resultant[axis]:
                pos[axis] += 1 if resultant[axis] > 0 else -1
        # check if calculated target is inside grid
        if 0 <= pos[0] < self.puzzle.w and 0 <= pos[1] < self.puzzle.h:
            return self.puzzle.grid[pos[0]][pos[1]][1]
        else:
            return conf.WALL

    def reaction (self, react_dir):
        if conf.DEBUG:
            print 'reaction', self, react_dir
        # handle reaction force from pushing something immoveable
        # remove forces on this axis
        axis = react_dir % 2
        react_on = []
        sources = self.sources[axis]
        for source in sources.keys():
            if source is not None:
                react_on.append(source)
            del sources[source]
        # redistribute diagonal forces
        targets = set(self.unhandled_targets[axis] + self.targets[axis].keys())
        u = self.unhandled_targets
        t = self.targets
        for axis in (0, 1):
            targets = set(u[axis] + t[axis].keys())
            for target in targets:
                p = target.pos
                if p[0] != self.pos[0] and p[1] != self.pos[1]:
                    # diagonal: remove
                    self.rm_targets(axis, target)
        # propagate reaction
        for b in react_on:
            b.reaction(react_dir)
        self.handled = False

    def update (self):
        if conf.DEBUG:
            print 'update:', self
        resultant = self.resultant()
        # check diagonal if need to
        if all(resultant):
            diag = self.target_tile(resultant)
        else:
            diag = False
        # check what's in target tiles on each axis and decide action to take
        react = [False] * 4
        for axis in (0, 1):
            force = resultant[axis]
            if not force:
                # no resultant force on this axis: reaction
                react[axis] = react[axis + 2] = True
                # won't push anything anyway
                continue
            # get adjacent target tile
            r = resultant[:]
            r[not axis] = 0
            adj = self.target_tile(r)
            if is_immoveable(adj):
                # can't move on this axis
                react[opposite_dir(force_dir(axis, force))] = True
                # so can't move diagonally
                self.rm_targets(axis, diag)
            else:
                if adj:
                    self.add_targets(axis, adj)
                if diag and not is_immoveable(diag):
                    self.add_targets(axis, diag)
        # if trying to move on both axes and can't move to diagonal
        if is_immoveable(diag) and not any(react):
            r = [abs(f) for f in resultant]
            if r[0] != r[1]:
                # unequal forces: reaction along weaker one's axis
                axis = r.index(min(r))
                force = resultant[axis]
                react[opposite_dir(force_dir(axis, force))] = True
            else:
                # equal forces: reaction along both axes
                for axis, force in enumerate(resultant):
                    react[opposite_dir(force_dir(axis, force))] = True
        # propagate any reactions
        for direction in xrange(len(react)):
            if react[direction]:
                self.reaction(direction)

        # apply forces to targets
        for axis in (0, 1):
            # remove old targets
            old = self.targets[axis]
            if old:
                self.rm_targets(axis, *old.keys())
            # distribute forces among new targets
            new = self.unhandled_targets[axis]
            if len(new) == 2:
                force = resultant[axis] / 2
                if force == 0:
                    # not enough force to do anything
                    self.targets[axis] = {}
                else:
                    self.targets[axis] = {new[0]: resultant[axis] - force,
                                          new[1]: force}
            elif len(new) == 1:
                self.targets[axis] = {new[0]: resultant[axis]}
            self.unhandled_targets[axis] = []
            # apply forces to targets
            for target, force in self.targets[axis].iteritems():
                if force != 0:
                    target.add_sources(axis, {self: force})

        self.handled = True

class Puzzle (object):
    def __init__ (self, game, definition, physics = False, **tiler_kw_args):
        self.lines = definition.split('\n')
        first = self._next_ints(self.lines)
        try:
            self.w, self.h = first
        except ValueError:
            # also got default surface
            self.w, self.h, self.default_s = first
        else:
            self.default_s = conf.DEFAULT_SURFACE
        self.size = (self.w, self.h)
        # grid handler
        self.tiler = Tiler(self.w, self.h, self.draw_tile, track_tiles = False,
                           **tiler_kw_args)
        self.physics = physics
        self.selected = None
        self.img = game.img
        self.init()

    def _next_ints (self, lines):
        try:
            line = lines.pop(0).strip()
        except IndexError:
            return None
        if line and line[0] == '#':
            # comment
            return self._next_ints(lines)
        else:
            try:
                return [int(c) for c in line.split(' ') if c]
            except ValueError:
                return False

    def init (self):
        self.tiler.reset()
        lines = self.lines[:]
        # create grid with default surface
        self.grid = []
        for i in xrange(self.w):
            col = []
            for j in xrange(self.h):
                col.append([self.default_s, None, False])
            self.grid.append(col)
        # create Block instances and place in grid
        self.blocks = []
        line = self._next_ints(lines)
        while line:
            type_ID, i, j = line
            b = (Block if self.physics else BoringBlock)(type_ID, self, [i, j])
            self.blocks.append(b)
            self.grid[i][j][1] = b
            line = self._next_ints(lines)
        # get non-default surface types
        line = self._next_ints(lines)
        while line:
            ID, i, j = line
            self.grid[i][j][0] = ID
            line = self._next_ints(lines)

    def add_block (self, block, x, y):
        # add a block, optionally creating it first
        pos = [x, y]
        if isinstance(block, BoringBlock):
            block.pos = pos
        else:
            # create block first; got (class, *args) tuple
            cls, type_ID = block[:2]
            args = block[2:]
            block = cls(type_ID, self, pos, *args)
        # remove existing block, if any
        self.rm_block(None, x, y)
        # add new block
        self.grid[x][y][1] = block
        self.blocks.append(block)
        self.tiler.change((x, y))

    def rm_block (self, block = None, x = None, y = None):
        # remove a block
        if block is None:
            if None not in (x, y):
                block = self.grid[x][y][1]
            # else got nothing
        else:
            x, y = block.pos
        if block is not None:
            self.grid[x][y][1] = None
            self.blocks.remove(block)
            self.tiler.change((x, y))
        # else passed nothing or tile has no block

    def mv_block (self, block, x, y):
        # move a block
        self.rm_block(block)
        self.add_block(block, x, y)

    def set_surface (self, x, y, surface = None):
        # set the surface at a tile
        if surface is None:
            surface = self.default_s
        self.grid[x][y][0] = surface
        self.tiler.change((x, y))

    def select (self, x, y):
        # set selected tile
        if self.selected is not None:
            self.deselect()
        if self.selected != [x, y]:
            self.grid[x][y][2] = True
            self.selected = [x, y]
            self.tiler.change(self.selected)

    def deselect (self):
        # deselect currently selected tile
        if self.selected is not None:
            x, y = self.selected
            self.grid[x][y][2] = False
            self.tiler.change(self.selected)
            self.selected = None

    def move_selected (self, direction, amount = 1):
        # move selection relative to current position
        selected = list(self.selected)
        axis = direction % 2
        selected[axis] += amount * (1 if direction > 1 else -1)
        selected[axis] %= self.size[axis]
        self.select(*selected)

    def resize (self, amount, direction):
        if amount == 0:
            return
        # resize one tile at a time
        # get new grid size
        axis = direction % 2
        sign = 1 if amount > 0 else -1
        size = list(self.size)
        size[axis] += sign
        if size[axis] == 0:
            # can't shrink
            return
        # get amount to offset everything by
        offset = [0, 0]
        offset[axis] += (sign - (1 if direction > 1 else -1)) / 2
        self.size = (w, h) = size
        # resize tiler
        self.tiler.w = w
        self.tiler.h = h
        self.tiler.reset()
        # create new grid
        grid = []
        di, dj = offset
        for i in xrange(w):
            col = []
            i -= di
            for j in xrange(h):
                j -= dj
                if 0 <= i < self.w and 0 <= j < self.h:
                    col.append(self.grid[i][j])
                else:
                    # doesn't come from current grid
                    col.append([self.default_s, None, False])
            grid.append(col)
        self.grid = grid
        self.w, self.h = self.size
        if self.selected is not None:
            # offset self.selected
            self.selected[0] += di
            self.selected[1] += dj
            x, y = self.selected
            # push selection back onto the grid
            if 0 <= x < self.w and 0 <= y < self.h:
                selected = list(self.selected)
            else:
                selected = self.selected
                for axis in (0, 1):
                    limit = self.size[axis] - 1
                    selected[axis] = min(max(selected[axis], 0), limit)
                self.selected = None
            self.select(*selected)
        self.resize(amount - sign, direction)

    def definition (self):
        """Return a definition string for the puzzle's current state."""
        # get blocks and surfaces from self.grid
        bs = []
        ss = []
        s_count = {}
        for i in xrange(len(self.grid)):
            col = self.grid[i]
            for j in xrange(len(col)):
                s, b, sel = col[j]
                if b is not None:
                    bs.append('{0} {1} {2}'.format(b.type, i, j))
                ss.append((s, '{0} {1} {2}'.format(s, i, j)))
                try:
                    s_count[s] += 1
                except KeyError:
                    s_count[s] = 1
        # get most common surface type to use as default
        # we only want one, so don't worry about types with the same freqency
        s_count = dict((v, k) for k, v in s_count.iteritems())
        common_s = s_count[max(s_count)]
        # compile definition
        return '{0} {1} {2}{3}{4}\n\n{5}'.format(
            self.w, self.h, common_s,
            '\n' if bs else '',
            '\n'.join(bs),
            # don't need individual tiles for most common surface
            '\n'.join(data for s, data in ss if s != common_s)
        )

    def step (self):
        # apply arrow forces
        for col in self.grid:
            for s, b, sel in col:
                if b is not None and s in conf.S_ARROWS:
                    b.add_force(conf.S_ARROWS.index(s), conf.FORCE_ARROW)

        # resolve forces into block destinations
        while 1:
            # handle contact forces
            while 1:
                unhandled = [b for b in self.blocks if not b.handled]
                if unhandled:
                    for b in unhandled:
                        b.update()
                else:
                    break

            # compile block destinations
            dest = {}
            for b in self.blocks:
                resultant = b.resultant()
                # get destination
                pos = b.pos[:]
                for axis, force in enumerate(resultant):
                    if force:
                        pos[axis] += 1 if force > 0 else -1
                if pos != b.pos:
                    # lists aren't hashable
                    pos = tuple(pos)
                    try:
                        dest[pos].append(b)
                    except KeyError:
                        dest[pos] = [b]
            if conf.DEBUG and dest:
                print dest

            # resolve conflicts
            rm = []
            for pos, bs in dest.iteritems():
                if len(bs) == 1:
                    dest[pos] = bs[0]
                else:
                    # check if highest force towards destination is unique
                    max_f = 0
                    for b in bs:
                        force = b.resultant()
                        force = abs(force[0]) + abs(force[1])
                        if force == max_f:
                            unique = False
                        elif force > max_f:
                            max_f = force
                            unique = b
                    if unique:
                        # move block with most force
                        dest[pos] = unique
                        bs.remove(unique)
                    else:
                        # don't move any blocks
                        rm.append(pos)
                    # reaction on all blocks that don't move
                    for b in bs:
                        diff = (b.pos[0] - pos[0], b.pos[1] - pos[1])
                        for axis in (0, 1):
                            if diff[axis]:
                                b.reaction(1 + axis + diff[axis])
            for pos in rm:
                del dest[pos]

            if not [b for b in self.blocks if not b.handled]:
                # done
                break

        if conf.DEBUG and dest:
            print dest

        # move blocks
        change = set()
        retain_forces = []
        for pos, b in dest.iteritems():
            # remove
            change.add(tuple(b.pos))
            self.grid[b.pos[0]][b.pos[1]][1] = None
            slide = self.grid[pos[0]][pos[1]][0] == conf.S_SLIDE
            if b.type in (conf.B_SLIDE, conf.B_BOUNCE) or slide:
                retain_forces.append(b)
        for pos, b in dest.iteritems():
            # add
            change.add(pos)
            b.pos = list(pos)
            self.grid[pos[0]][pos[1]][1] = b
        self.tiler.change(*change)
        # reset forces
        for b in self.blocks:
            b.reset(b in retain_forces)

    def _draw_from_img (self, surface, rect, prefix, ID):
        ID = prefix + str(ID)
        fn = conf.IMG_DIR + ID + '.png'
        if exists(fn):
            # image might be transparent
            if prefix == 's':
                surface.fill(conf.BG, rect)
            surface.blit(self.img(ID, fn, rect), rect)
            return True
        return False

    def draw_tile (self, surface, rect, i, j):
        # draw a single tile; called by Tiler
        s, b, selected = self.grid[i][j]
        # surface
        if s < 0:
            # blit image if exists, else use colour
            if self._draw_from_img(surface, rect, 's', s):
                colour = ()
            else:
                colour = conf.surface_colours[s]
        else:
            # goal: use block colour
            colour = conf.block_colours[s]
        if colour:
            surface.fill(colour, rect)
        # selection ring
        if selected:
            width = max(int(rect[2] * conf.SEL_WIDTH), conf.MIN_SEL_WIDTH)
            draw_rect(surface, conf.SEL_COLOUR, rect, width)
        # block
        if b is not None:
            if b.type < conf.MIN_CHAR_ID:
                # blit image if exists, else use colour
                if not self._draw_from_img(surface, rect, 'b', b.type):
                    rect = pygame.Rect(rect)
                    p = rect.center
                    r = rect.w / 2
                    pygame.draw.circle(surface, (0, 0, 0), p, r)
                    pygame.draw.circle(surface, conf.block_colours[b.type], p, int(r * .8))
            else:
                # draw character in tile
                c = b.type
                if c < conf.SELECTED_CHAR_ID_OFFSET:
                    # normal
                    colour = conf.PUZZLE_TEXT_COLOUR
                elif c < conf.SPECIAL_CHAR_ID_OFFSET:
                    # selected
                    c -= conf.SELECTED_CHAR_ID_OFFSET
                    colour = conf.PUZZLE_TEXT_SELECTED_COLOUR
                else:
                    # special
                    c -= conf.SPECIAL_CHAR_ID_OFFSET
                    colour = conf.PUZZLE_TEXT_SPECIAL_COLOUR
                # render character
                c = chr(c).upper() if conf.PUZZLE_TEXT_UPPER else chr(c)
                text = self.img((b.type, rect[3]), ((conf.PUZZLE_FONT, rect[3], False), c,
                                         colour), text = True)
                # centre inside tile rect
                source = autocrop(text)
                if source: # else blank
                    target = (rect[0] + (rect[2] - source[2]) / 2,
                            rect[1] + (rect[3] - source[3]) / 2)
                    surface.blit(text, target, source)

    def draw (self, screen, everything = False, size = None):
        # draw grid and tiles
        if everything:
            self.tiler.reset()
        rects = self.tiler.draw_changed(screen, size)
        if rects is None:
            return None
        elif isinstance(rects[0], int):
            return True
        else:
            return rects[1:]