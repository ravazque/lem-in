# lem-in

lem-in is a digital ant farm written in **C**. It reads a colony on standard
input — ants, rooms and tunnels — and prints the movements that take every ant
from `##start` to `##end` in as few turns as possible, knowing that no room
except the start and the end may hold more than one ant at a time. The bonus,
`visu-hex`, is a windowed visualizer written in Python with tkinter that
replays and checks the result.

## Layout

```
lem-in/
│
├── bonus/             visu-hex + visu_hex/    # bonus: ./lem-in < map | ./visu-hex
├── include/                                   # types, constants, prototypes
├── lib/               libft                   # the only helper library used
├── maps/              valid/ invalid/ stress/ # test colonies, `make maps` adds the big ones
│
└── srcs/
    ├── utils/         memory cleanup
    ├── parsing/       read, validate, store the colony
    ├── graph/         adjacency lists, node splitting, room lookup
    ├── solver/        min-cost max flow, route extraction, route and ant selection
    ├── simulation/    turn-by-turn output
    │
    └── main.c                                 # parse → build → solve → simulate
```

Build with `make`, run with `./lem-in < map`, clean with `make fclean`. The
program takes no arguments: the colony comes in on stdin, the simulation goes
out on stdout, and any error prints `ERROR` on stderr with exit status 1.
`make bonus` links `./visu-hex` to the visualizer.

## Concepts

| Term | Meaning in this project |
|------|-------------------------|
| Colony | The whole input: ant count, rooms, tunnels, `##start` and `##end` |
| Room | A graph node; holds at most one ant, except the start and the end |
| Tunnel | An undirected edge between two rooms, usable by one ant per turn |
| Turn | One step in which every ant may move to an adjacent free room |
| Route | A room sequence from start to end taken by a block of ants |
| Node splitting | Room → `in`/`out` pair joined by a capacity-1 edge |
| Residual graph | The directed graph max flow works on: forward and reverse edges |
| Max flow | Number of routes that share no room, found by min-cost max flow |

## The problem

A single shortest path is not the answer. Because a room holds one ant, ants
queued behind each other on one route arrive one per turn, so a colony with
`n` ants and a shortest route of length `len` needs `len + n - 1` turns that
way. Spreading ants over several routes that share no room lets them advance in
parallel, which is almost always faster — but only up to a point, since a route
much longer than the shortest one can delay the very last ant.

So the program has to answer two questions: **which** sets of room-disjoint
routes exist, and **how many** of them are worth using.

## How it works

**Parsing.** The whole of stdin is read into one growable buffer and cut into
lines in place, so there is no syscall per line. The first line must be a
positive integer that fits an `int` — the conversion stops as soon as the value
passes `INT_MAX`, so a 20-digit count cannot wrap around into a small one.
`##start` and `##end` mark the next room to be declared and may appear only
once each; any other `#…` line is a comment. A room is `name x y` with exactly
three fields, integer coordinates that fit an `int` (negative included), and a
name that starts with neither `L` nor `#`. A tunnel is `a-b` between two different, already declared
rooms; a tunnel declared twice counts once. Names are resolved through a djb2
hash table with chaining, so a link never scans the room array. Every accepted line is also duplicated into an echo
buffer, because the map has to be reprinted before the moves. An empty or
malformed line stops everything with `ERROR`.

**Node splitting.** Max flow limits edges, not nodes, so each room `i` is split
into `in = 2i` and `out = 2i+1` joined by an edge of capacity 1. A tunnel `a-b`
becomes `out(a) → in(b)` and `out(b) → in(a)`, both capacity 1. Any unit of flow
crossing a room saturates that room's internal edge, which is exactly the
one-ant-per-room rule. Flow runs from `out(start)` to `in(end)`, so the internal
edges of the start and end rooms are never on the path and never constrain them.

**Min-cost max flow.** Every forward edge costs `+1` and its residual reverse
costs `-1`, so undoing an earlier choice refunds its length. Each pass pushes
one unit along the *cheapest* augmenting path, which keeps the total length of
the routes minimal for that flow value. The search is Dijkstra over the residual
graph with Johnson potentials (`pot[v]` shifted by the previous distance) so the
negative reverse costs become non-negative, and a bucket queue settles nodes in
`O(1)`. With unit capacities the final flow value is exactly the number of
room-disjoint routes; a flow of 0 means start and end are disconnected, which is
an error.

**Route extraction.** The flow is a set of saturated edges, not a list of
routes, so it has to be decomposed. One route is walked per saturated edge
leaving `out(start)`, a cursor making sure no edge is taken twice; from there
each node has a single outgoing unit of flow, so the walk just follows the
saturated forward edges to `in(end)`. Rooms taken by an earlier route are marked
so a cycle can never trap the walk. Each walk yields one route, stored as room
ids with the `in`/`out` duplicates collapsed.

**Route and ant selection.** Routes are sorted by length, shortest first. A
route of length `len` delivers `t - len + 1` ants by turn `t`, so the turns
needed by the `k` shortest routes are the smallest `t` whose total capacity
reaches the ant count — found by binary search. Every `k` from 1 to the max flow
is evaluated and the one with the fewest turns is kept; the rest are freed. A
`k` that cannot beat the best turn count already found is never decomposed, and
the search stops once the best equals the shortest route. This covers the true
optimum: by Ford and Fulkerson's theorem on dynamic flows, no schedule — even
one letting ants wait or share rooms at different times — beats the best
temporally repeated static flow, which is what a set of disjoint routes is.
The ants are then spread by filling every route up to that turn limit and
dropping the surplus from the longest ones.

**Simulation.** Each route receives a contiguous block of ant ids. Ant `j`
(0-based within its route) leaves on turn `j+1` and on turn `t` stands in
`rooms[t - j]`, so a turn is emitted by walking the routes and printing every
ant currently between the start and the end. Everything — the echoed map, the
blank line, all the turns — goes through a 64 KB buffer flushed whenever it
fills, so memory stays flat however long the simulation runs.

## Visualizer

Built with `make bonus` and used as the subject describes it,
`./lem-in < map | ./visu-hex`. It is Python 3 with `tkinter`, the GUI toolkit
that ships with Python, so nothing has to be installed with pip; it reads the
simulation on stdin and opens a resizable window.

Two views, switched with `v`. The **map** view places the rooms at their
coordinates — or, when those carry no shape, as on the generator's maps whose
rooms all sit on the `x == y` diagonal, lays them out from the graph: one
column per distance from `##start`, rows ordered so that tunnels stay short —
draws the tunnels, marks `S` and `E` with the number of ants waiting or
arrived, outlines the rooms of the routes in use in their route's colour and
glides a coloured dot per ant along the tunnels between two turns; drag pans,
the wheel zooms. The **lanes** view draws one lane per route the ants actually
followed, shortest first, which makes the flow legible — short routes
saturate, long ones carry a single wave — and is what opens first on the
generator's maps. Around the view: turn and speed, colony figures, how many
ants are still in `##start`, on the way or home, and a verdict — the
visualizer re-checks every move (one per ant, through a tunnel, into a free
room, never out of `##end`, everybody home at the end) and names the first
offending turn otherwise. `space` plays, `←`/`→` step, `+`/`-` change the
speed, `q` quits; a `##visu speed=4 paused view=lanes` line in the colony sets
the defaults, and `--dump DIR` writes frames as PostScript without a
window, for tests.

## Testing

Three colonies that ship with the repository, from the smallest to the largest;
each line prints the simulation and hands it to the visualizer (`q` quits):

```bash
make bonus
./lem-in < maps/valid/example.map | ./visu-hex                      # simple: 3 ants, 2 routes
./lem-in < maps/valid/hundred_ants.map | ./visu-hex --speed 4       # normal: 124 ants, 523 rooms
./lem-in < maps/stress/big_superposition.map | ./visu-hex --speed 8 # big: 164 ants, 2 893 rooms
```

Drop the `| ./visu-hex` to see the raw output.

## What gets rejected

| Case | Example map |
|------|-------------|
| Ant count missing, zero, negative, not a number or beyond `INT_MAX` | `ants_*.map`, `no_ants.map`, `overflow_ants.map` |
| Empty input, or an empty line anywhere | `empty.map`, `blank_line_middle.map` |
| Room with too few or too many fields | `room_missing_field.map`, `room_extra_field.map` |
| Non-integer or overflowing coordinates | `coords_not_int.map`, `overflow_coords.map` |
| Room name starting with `L` or `#` | `room_name_starts_L.map`, `room_name_starts_hash.map` |
| Duplicate room name | `dup_room.map` |
| Two `##start` or two `##end` | `dup_start.map`, `dup_end.map` |
| No `##start` or no `##end` | `no_start.map`, `no_end.map` |
| Tunnel naming an undeclared room | `link_unknown_room.map` |
| Tunnel from a room to itself | `self_link.map` |
| Valid colony with no route between start and end | `no_path.map` |

## Complexity

With `R` rooms, `T` tunnels and `A` ants, the split graph has `V = 2R` nodes and
`E = 2R + 4T` directed edges counting the residual reverses.

| Stage | Cost |
|-------|------|
| Parsing | `O(R + T)` amortised, hash lookups in `O(1)` |
| Graph construction | `O(R + T)` |
| Min-cost max flow | `O(F * (V + E))`, `F` bounded by the degree of start and end |
| Route extraction | `O(V + E)` |
| Route selection | `O(F * F * log A)` — one binary search per candidate count |
| Ant distribution | `O(F)` |
| Simulation | `O(turns * A)` output tokens, flushed every 64 KB |

Measured: the generator's `--big` and `--big-superposition` colonies solve in
under 50 ms; of the stress colonies of `make maps`, the 100×100 grid and the
4 000 rooms with 60 000 tunnels take a quarter of a second, the 100 000-room
corridor and the 5 000 disjoint routes about one.

## Summary

- **Parsing** — one read, in-place line splitting, strict validation, hash table
  for name lookup, and the input kept for the echo.
- **Modelling** — every room split into `in`/`out` with a capacity-1 edge, which
  turns "one ant per room" into a plain edge capacity.
- **Solving** — min-cost max flow gives the shortest room-disjoint routes; the
  flow is then decomposed into explicit room sequences.
- **Optimising** — the route count and the ant distribution are chosen to
  minimise the turn on which the last ant arrives.
- **Output** — the map, a blank line, then one line of `Lx-room` tokens per
  turn, flushed in fixed-size blocks.
- **Bonus** — a tkinter visualizer that replays, validates and animates the run.

## References

Algorithms:

- Maximum flow problem — <https://en.wikipedia.org/wiki/Maximum_flow_problem>
- Minimum-cost flow problem — <https://en.wikipedia.org/wiki/Minimum-cost_flow_problem>
- Johnson's algorithm (potentials) — <https://en.wikipedia.org/wiki/Johnson%27s_algorithm>
- Ford-Fulkerson method — <https://en.wikipedia.org/wiki/Ford%E2%80%93Fulkerson_algorithm>
- Ford & Fulkerson, *Constructing maximal dynamic flows from static flows*
  (1958) — <https://doi.org/10.1287/opre.6.3.419>
- Max-flow min-cut theorem — <https://en.wikipedia.org/wiki/Max-flow_min-cut_theorem>
- Menger's theorem (disjoint paths and connectivity) —
  <https://en.wikipedia.org/wiki/Menger%27s_theorem>
- Vertex capacities by node splitting —
  <https://cp-algorithms.com/graph/edmonds_karp.html>
- Breadth-first search — <https://en.wikipedia.org/wiki/Breadth-first_search>
- Suurballe's algorithm, the shortest-pair variant of the same idea —
  <https://en.wikipedia.org/wiki/Suurballe%27s_algorithm>

Bonus:

- Python `tkinter` — <https://docs.python.org/3/library/tkinter.html>
