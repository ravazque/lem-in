"""Geometry shared by every view: where a room goes on the screen."""


def collinear(rooms):
    if len(rooms) < 3:
        return True
    ax, ay = rooms[0].x, rooms[0].y
    base = None
    for room in rooms[1:]:
        if base is None:
            if room.x != ax or room.y != ay:
                base = (room.x - ax, room.y - ay)
        elif (room.x - ax) * base[1] != (room.y - ay) * base[0]:
            return False
    return True


def _barycentre(colony, depth, row, room, column):
    near = [row[o] for o in colony.adj[room] if depth[o] == column]
    return sum(near) / len(near) if near else row[room]


def auto_coords(colony, routes):
    """Layout for maps whose coordinates carry no shape (the generator puts
    every room on x == y): column = distance from S, rows by barycentre."""
    depth = [-1] * len(colony.rooms)
    depth[colony.start] = 0
    queue = [colony.start]
    for room in queue:
        for other in colony.adj[room]:
            if depth[other] < 0:
                depth[other] = depth[room] + 1
                queue.append(other)
    far = max(depth) + 1
    layers = {}
    for room in range(len(colony.rooms)):
        if depth[room] < 0:
            depth[room] = far
        layers.setdefault(depth[room], []).append(room)
    rank = {}
    for route in routes:
        for i, room in enumerate(route.rooms):
            rank.setdefault(room, (route.index, i))
    for rooms in layers.values():
        rooms.sort(key=lambda r: rank.get(r, (len(routes), r)))
    columns = sorted(layers)
    row = {}
    for rooms in layers.values():
        for i, room in enumerate(rooms):
            row[room] = (i + 0.5) / len(rooms)
    for sweep in range(4):
        step = 1 if sweep % 2 else -1
        for column in (columns if step < 0 else columns[::-1])[1:]:
            rooms = layers[column]
            rooms.sort(key=lambda r: _barycentre(colony, depth, row, r,
                                                 column + step))
            for i, room in enumerate(rooms):
                row[room] = (i + 0.5) / len(rooms)
    tallest = max(len(rooms) for rooms in layers.values())
    unit = max(0.02, 0.6 * max(1, len(columns) - 1) / tallest)
    coords = [None] * len(colony.rooms)
    for rooms in layers.values():
        for i, room in enumerate(rooms):
            coords[room] = (depth[room], (i - (len(rooms) - 1) / 2.0) * unit)
    return coords, min(1.0, unit)


def nearest_pitch(coords):
    """10th percentile of the nearest-neighbour distances, found in x order."""
    points = sorted(coords)
    if len(points) < 2:
        return 1.0
    gaps = []
    for i, (x, y) in enumerate(points):
        best = None
        for j in range(i + 1, min(len(points), i + 9)):
            ox, oy = points[j]
            d = ((ox - x) ** 2 + (oy - y) ** 2) ** 0.5
            if best is None or d < best:
                best = d
        if best is not None:
            gaps.append(best)
    gaps.sort()
    return max(gaps[len(gaps) // 10], 1e-9)


class MapLayout:
    """Scales coordinates to width x height with zoom and pan, keeping the
    aspect (`cell_aspect` = height / width of one unit: 2 for a terminal)."""

    def __init__(self, colony, cell_aspect=1.0, coords=None, pitch=None):
        self.colony = colony
        self.aspect = cell_aspect
        if coords is None:
            coords = [(r.x, r.y) for r in colony.rooms]
        self.coords = coords
        self.pitch_units = pitch if pitch else nearest_pitch(coords)
        xs = [x for x, y in coords]
        ys = [y for x, y in coords]
        self.min_x, self.max_x = min(xs), max(xs)
        self.min_y, self.max_y = min(ys), max(ys)
        self.zoom = 1.0
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.width = self.height = 0
        self.margin = 0
        self.scale = 1.0
        self.positions = []

    def resize(self, width, height, margin):
        self.width, self.height, self.margin = width, height, margin
        self._compute()

    def zoom_by(self, factor, min_zoom=0.25, max_zoom=64.0):
        self.zoom = max(min_zoom, min(max_zoom, self.zoom * factor))
        self._compute()

    def pan_by(self, dx, dy):
        self.pan_x += dx
        self.pan_y += dy
        self._compute()

    def reset(self):
        self.zoom, self.pan_x, self.pan_y = 1.0, 0.0, 0.0
        self._compute()

    def _compute(self):
        span_x = max(1, self.max_x - self.min_x)
        span_y = max(1, self.max_y - self.min_y)
        usable_w = max(1, self.width - 2 * self.margin)
        usable_h = max(1, self.height - 2 * self.margin)
        scale = min(usable_w / span_x, usable_h * self.aspect / span_y)
        self.scale = scale * self.zoom
        drawn_w = span_x * self.scale
        drawn_h = span_y * self.scale / self.aspect
        off_x = (self.width - drawn_w) / 2.0 + self.pan_x
        off_y = (self.height - drawn_h) / 2.0 + self.pan_y
        self.positions = [
            (off_x + (x - self.min_x) * self.scale,
             off_y + (y - self.min_y) * self.scale / self.aspect)
            for x, y in self.coords]

    def pitch(self):
        return self.pitch_units * self.scale / self.aspect

    def spacing(self):
        links = self.colony.links[:2000]
        if not links:
            return self.width
        total = 0.0
        for a, b in links:
            (ax, ay), (bx, by) = self.positions[a], self.positions[b]
            total += max(abs(ax - bx), abs(ay - by))
        return total / len(links)


class LaneLayout:
    def __init__(self, replay):
        self.routes = replay.routes
        self.column = []
        for route in self.routes:
            cols = {}
            for i, room in enumerate(route.rooms):
                cols.setdefault(room, i)
            self.column.append(cols)
        self.longest = max((r.length for r in self.routes), default=0)

    def locate(self, route_index, room):
        if route_index < 0 or route_index >= len(self.routes):
            return None
        return self.column[route_index].get(room)
