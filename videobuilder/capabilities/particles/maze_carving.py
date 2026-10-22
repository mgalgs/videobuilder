"""Maze Carving: a grid of closed cells has its walls knocked out one at a
time by a wandering cursor, which backs up when it is boxed in, until every
cell is joined and a finished maze is left."""
import random

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def carve_maze(cols, rows, seed=0, start=(0, 0)):
    """The moves of a depth-first (recursive backtracker) maze carve over a
    `cols` x `rows` grid, as `(a, b, forward)` triples of `(col, row)` cells:
    `forward` moves knock out the wall between `a` and `b`, the rest are the
    cursor backing up from `a` to `b`. Deterministic for a given `seed`. The
    carved walls form a perfect maze: one route between any two cells."""
    rng = random.Random(seed)
    seen = {start}
    stack = [start]
    moves = []
    while stack:
        c, r = stack[-1]
        options = [(c + dc, r + dr) for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1))
                   if 0 <= c + dc < cols and 0 <= r + dr < rows and (c + dc, r + dr) not in seen]
        if options:
            nxt = rng.choice(options)
            seen.add(nxt)
            moves.append((stack[-1], nxt, True))
            stack.append(nxt)
        else:
            stack.pop()
            if stack:
                moves.append(((c, r), stack[-1], False))
    return moves


def maze_state(moves, k, start=(0, 0)):
    """After the first `k` of `moves`: the set of carved walls (each a
    frozenset of two cells), the set of visited cells, and the cursor's
    current route back to the start (a list of cells, the cursor last)."""
    carved, visited, stack = set(), {start}, [start]
    for a, b, forward in moves[:k]:
        if forward:
            carved.add(frozenset((a, b)))
            visited.add(b)
            stack.append(b)
        else:
            stack.pop()
    return carved, visited, stack


def draw_maze(cv, x, y, cols, rows, cell, moves, p, wall=demo.INK, floor=demo.TEAL, trail=demo.ACCENT,
              head='#f2b33d', wall_width=3, start=(0, 0)):
    """Draw the maze carved by `moves` (from `carve_maze`) at progress `p`
    (0 -> 1 over all moves), its top-left corner at (x, y), `cell` px per
    square. Visited cells get a faint `floor` tint, the cursor's open route is
    a `trail` line, the cursor a `head` dot; walls still standing are drawn
    in `wall`. At `p` = 1 only the finished maze remains."""
    exact = vb.clamp01(p) * len(moves)
    k = int(exact)
    carved, visited, stack = maze_state(moves, k, start)
    for c, r in visited:
        cv.rect(x + c * cell, y + r * cell, cell, cell, floor, alpha=0.16)
    centre = lambda q: (x + (q[0] + 0.5) * cell, y + (q[1] + 0.5) * cell)  # noqa: E731
    pts = [centre(q) for q in stack]
    if k < len(moves):  # the cursor glides part-way along its next move
        a, b, _ = moves[k]
        f = exact - k
        (ax, ay), (bx, by) = centre(a), centre(b)
        tip = (ax + (bx - ax) * f, ay + (by - ay) * f)
        if moves[k][2]:
            pts.append(tip)
        else:
            pts[-1] = tip
    if p < 1 and len(pts) > 1:
        ctx = cv.ctx
        ctx.save()
        ctx.new_path()
        ctx.move_to(*pts[0])
        for q in pts[1:]:
            ctx.line_to(*q)
        ctx.set_source_rgba(*vb.rgba(trail, 0.85))
        ctx.set_line_width(cell * 0.22)
        ctx.set_line_join(1)  # round
        ctx.set_line_cap(1)
        ctx.stroke()
        ctx.restore()
    cv.ctx.save()
    cv.ctx.set_line_cap(2)  # square, so wall ends meet without notches
    for r in range(rows):
        for c in range(cols):
            x0, y0 = x + c * cell, y + r * cell
            if c + 1 < cols and frozenset(((c, r), (c + 1, r))) not in carved:
                cv.line(x0 + cell, y0, x0 + cell, y0 + cell, wall, width=wall_width)
            if r + 1 < rows and frozenset(((c, r), (c, r + 1))) not in carved:
                cv.line(x0, y0 + cell, x0 + cell, y0 + cell, wall, width=wall_width)
    cv.ctx.restore()
    cv.outline(x, y, cols * cell, rows * cell, wall, width=wall_width)
    if p < 1:
        demo.dot(cv, *pts[-1], r=cell * 0.2, color=head)
    cv.mark('maze', x, y, cols * cell, rows * cell)


COLS, ROWS, CELL = 16, 9, 48


def draw(n, cv):
    x, y = (demo.W - COLS * CELL) / 2, (demo.H - ROWS * CELL) / 2
    draw_maze(cv, x, y, COLS, ROWS, CELL, MOVES, demo.phase(n, 0.3, 2.6))


MOVES = carve_maze(COLS, ROWS, seed=7)


TECHNIQUE = Technique(
    id='maze-carving',
    name='Maze carving',
    family='particles',
    group='Tiling & patterns',
    aliases=('recursive backtracker maze', 'Prim maze', 'maze generation', 'labyrinth build'),
    definition='A cursor wanders through a grid of boxed-in squares, breaking down the wall in front of it '
               'and backing up at dead ends, until every square is linked into one finished maze.',
    phrasings=('show a maze getting dug out square by square',
               'animate a labyrinth generating itself on a grid',
               'a little dot carves a maze, backtracking when it gets stuck'),
    related=('voxel-build', 'pattern-tiling', 'recursive-tree', 'follow-through', 'extrusion',
             'reverse-motion-cut'),
    api=('videobuilder.techniques.particles.maze_carving.draw_maze',
         'videobuilder.techniques.particles.maze_carving.carve_maze',
         'videobuilder.techniques.particles.maze_carving.maze_state'),
    demo=lambda: demo.film(draw),
)
