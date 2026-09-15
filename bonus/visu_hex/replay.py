"""Replays the moves: where every ant is on any turn, the routes the ants
followed, and whether the simulation respects the rules of the subject."""

from array import array

SNAPSHOT_BUDGET = 64 * 1024 * 1024
MAX_SNAPSHOTS = 64


def pairs(moves):
    return zip(moves[0::2], moves[1::2])


class Route:
    __slots__ = ('rooms', 'ants', 'index')

    def __init__(self, rooms):
        self.rooms = rooms
        self.ants = 0
        self.index = 0

    @property
    def length(self):
        return len(self.rooms) - 1


class State:
    __slots__ = ('turn', 'pos', 'counts', 'occupant')

    def __init__(self, pos, at_start, at_end, occupant, turn):
        self.turn = turn
        self.pos = array('i', pos)
        self.counts = [at_start, at_end]
        self.occupant = dict(occupant)


class Replay:
    """turns[t] holds the moves of turn t+1; a position array is indexed by ant
    (slot 0 unused) and holds the room id, every ant starting in ##start."""

    def __init__(self, colony, turns):
        self.colony = colony
        self.turns = turns
        self.count = len(turns)
        self.errors = []
        self.routes = []
        self.route_of = array('i', [0]) * (colony.ants + 1)
        per_snapshot = 4 * (colony.ants + 1)
        keep = max(1, min(MAX_SNAPSHOTS, SNAPSHOT_BUDGET // per_snapshot))
        self._snap_every = max(1, -(-self.count // keep))
        self._snaps = {}
        self._state = None
        self._scan()

    def _scan(self):
        colony = self.colony
        start, end = colony.start, colony.end
        pos = array('i', [start]) * (colony.ants + 1)
        counts = [colony.ants, 0]
        occupant = {}
        node_of = array('i', [0]) * (colony.ants + 1)
        trie, trie_room, trie_parent = [{}], [start], [-1]
        self._snaps[0] = (array('i', pos), counts[0], counts[1], {})
        for t, moves in enumerate(self.turns, 1):
            self._check_turn(t, moves, pos, occupant)
            for ant, room in pairs(moves):
                here = pos[ant]
                if occupant.get(here) == ant:
                    del occupant[here]
            for ant, room in pairs(moves):
                self._count(pos[ant], counts, -1)
                pos[ant] = room
                self._count(room, counts, 1)
                if room != start and room != end:
                    occupant[room] = ant
                node = node_of[ant]
                child = trie[node].get(room)
                if child is None:
                    child = len(trie)
                    trie[node][room] = child
                    trie.append({})
                    trie_room.append(room)
                    trie_parent.append(node)
                node_of[ant] = child
            if t % self._snap_every == 0:
                self._snaps[t] = (array('i', pos), counts[0], counts[1],
                                  dict(occupant))
        left = colony.ants - counts[1]
        if left:
            self.errors.append('%d ant%s never reached ##end'
                               % (left, 's' if left > 1 else ''))
        self._build_routes(node_of, trie_room, trie_parent)

    def _count(self, room, counts, delta):
        if room == self.colony.start:
            counts[0] += delta
        elif room == self.colony.end:
            counts[1] += delta

    def _check_turn(self, t, moves, pos, occupant):
        """The subject's rules, checked before the turn applies: one move per
        ant, through a tunnel, into a free or vacated room, never out of E."""
        colony = self.colony
        movers = set(moves[0::2])
        seen = set()
        targets = {}
        for ant, room in pairs(moves):
            here = pos[ant]
            if ant in seen:
                self._error(t, 'L%d moves twice' % ant)
            seen.add(ant)
            if here == colony.end:
                self._error(t, 'L%d leaves ##end' % ant)
            elif room not in colony.adj[here]:
                self._error(t, 'no tunnel %s-%s for L%d'
                            % (colony.name(here), colony.name(room), ant))
            if room == colony.start or room == colony.end:
                continue
            holder = occupant.get(room)
            if room in targets:
                self._error(t, 'L%d and L%d both enter %s'
                            % (targets[room], ant, colony.name(room)))
            elif holder is not None and holder not in movers:
                self._error(t, '%s is occupied by L%d when L%d enters'
                            % (colony.name(room), holder, ant))
            targets[room] = ant

    def _error(self, turn, text):
        if len(self.errors) < 8:
            self.errors.append('turn %d: %s' % (turn, text))

    def _build_routes(self, node_of, trie_room, trie_parent):
        by_node = {}
        for ant in range(1, self.colony.ants + 1):
            leaf = node_of[ant]
            if leaf == 0:
                continue
            route = by_node.get(leaf)
            if route is None:
                rooms = []
                node = leaf
                while node >= 0:
                    rooms.append(trie_room[node])
                    node = trie_parent[node]
                rooms.reverse()
                route = by_node[leaf] = Route(rooms)
            route.ants += 1
        routes = sorted(by_node.values(), key=lambda r: (r.length, r.rooms))
        for i, route in enumerate(routes):
            route.index = i
        for ant in range(1, self.colony.ants + 1):
            route = by_node.get(node_of[ant])
            self.route_of[ant] = route.index + 1 if route else 0
        self.routes = routes

    @property
    def valid(self):
        return not self.errors

    def _seek(self, turn):
        turn = max(0, min(turn, self.count))
        state = self._state
        if state is None or turn < state.turn \
                or turn - state.turn > self._snap_every:
            base = (turn // self._snap_every) * self._snap_every
            while base not in self._snaps:
                base -= self._snap_every
            state = self._state = State(*self._snaps[base], turn=base)
        start, end = self.colony.start, self.colony.end
        pos, counts, occupant = state.pos, state.counts, state.occupant
        while state.turn < turn:
            moves = self.turns[state.turn]
            for ant, room in pairs(moves):
                if occupant.get(pos[ant]) == ant:
                    del occupant[pos[ant]]
            for ant, room in pairs(moves):
                self._count(pos[ant], counts, -1)
                pos[ant] = room
                self._count(room, counts, 1)
                if room != start and room != end:
                    occupant[room] = ant
            state.turn += 1
        return state

    def positions(self, turn):
        return self._seek(turn).pos

    def transit(self, turn):
        return self._seek(turn).occupant

    def census(self, turn):
        counts = self._seek(turn).counts
        return counts[0], self.colony.ants - counts[0] - counts[1], counts[1]

    def moves(self, turn):
        if turn < 1 or turn > self.count:
            return []
        before = array('i', self.positions(turn - 1))
        return [(ant, before[ant], room)
                for ant, room in pairs(self.turns[turn - 1])]
