"""series_emulator.apu — заготовка звукового модуля (PCM-микшер)."""
from __future__ import annotations


class AudioBuffer:
    def __init__(self, sample_rate: int = 48000, channels: int = 2):
        self.sample_rate = sample_rate
        self.channels = channels
        self._queued = []

    def submit(self, samples):
        """samples — список float-значений [-1.0 .. 1.0] в stereo-чередовании."""
        cleaned = [max(-1.0, min(1.0, float(x))) if x is not None else 0.0
                   for x in samples]
        self._queued.append(cleaned)
        return len(cleaned)

    def mix(self, frames: int):
        """Складывает очередь в один список длиной frames*channels."""
        out = [0.0] * (frames * self.channels)
        for chunk in self._queued:
            for i, sample in enumerate(chunk):
                if i < len(out):
                    out[i] += sample
        self._queued = []
        return out


class APU:
    def __init__(self, sample_rate: int = 48000, channels: int = 2):
        self.main = AudioBuffer(sample_rate, channels)

    def status(self) -> dict:
        return {"sample_rate": self.main.sample_rate,
                "channels": self.main.channels}
