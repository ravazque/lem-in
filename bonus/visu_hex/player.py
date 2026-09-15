"""Playback state: which turn is shown and how far into the next move."""


class Player:
    def __init__(self, replay, speed, paused):
        self.replay = replay
        self.turn = 0
        self.phase = 0.0
        self.speed = speed
        self.playing = not paused and replay.count > 0

    def advance(self, seconds):
        if not self.playing:
            return
        self.phase += seconds * self.speed
        while self.phase >= 1.0:
            self.phase -= 1.0
            self.turn += 1
            if self.turn >= self.replay.count:
                self.turn = self.replay.count
                self.phase = 0.0
                self.playing = False
                return

    def seek(self, turn):
        self.turn = max(0, min(self.replay.count, turn))
        self.phase = 0.0

    def toggle(self):
        if self.turn >= self.replay.count:
            self.seek(0)
        self.playing = not self.playing

    def faster(self, factor):
        self.speed = max(0.1, min(60.0, self.speed * factor))
