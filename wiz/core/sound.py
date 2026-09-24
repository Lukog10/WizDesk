"""Procedural organic sound effects engine and player for Wiz companion mascot."""

import math
import struct
import wave
from pathlib import Path
from typing import Dict, Optional, Tuple, List
from PyQt6.QtCore import QObject, QUrl
from PyQt6.QtMultimedia import QSoundEffect

from wiz.core.config import config


class WavSynthesizer:
    """Generates organic, high-fidelity 16-bit 44.1kHz PCM mono WAV files programmatically."""

    SAMPLE_RATE = 44100

    @classmethod
    def _write_wav(cls, output_path: Path, samples: List[float]) -> None:
        """Write floating-point samples (-1.0 to 1.0) to a 16-bit PCM WAV file."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(output_path), "wb") as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(cls.SAMPLE_RATE)
            packed = bytearray()
            for s in samples:
                clamped = max(-1.0, min(1.0, s))
                int_val = int(clamped * 32767.0)
                packed.extend(struct.pack("<h", int_val))
            wav_file.writeframes(packed)

    @classmethod
    def generate_all(cls, sounds_dir: Path) -> Dict[str, Path]:
        """Generate all procedural sound files if not already present."""
        sound_map: Dict[str, Path] = {}
        generators = {
            "wake_up": cls._create_wake_up,
            "sleep": cls._create_sleep,
            "task_complete": cls._create_task_complete,
            "task_notify": cls._create_task_notify,
            "task_cancel": cls._create_task_cancel,
            "work_log": cls._create_work_log,
            "mascot_poke": cls._create_mascot_poke,
            "mascot_drag_start": cls._create_mascot_drag_start,
            "mascot_drag_end": cls._create_mascot_drag_end,
        }

        for name, gen_fn in generators.items():
            path = sounds_dir / f"{name}.wav"
            if not path.exists() or path.stat().st_size == 0:
                samples = gen_fn()
                cls._write_wav(path, samples)
            sound_map[name] = path

        return sound_map

    @classmethod
    def _tone(cls, freq: float, duration_s: float, attack_s: float = 0.01, decay_s: float = 0.05,
              harmonics: Tuple[Tuple[float, float], ...] = ((1.0, 1.0), (2.0, 0.25), (3.0, 0.08))) -> List[float]:
        """Generate an organic tone with harmonic overtone blending and an exponential decay envelope."""
        total_samples = int(cls.SAMPLE_RATE * duration_s)
        samples = []
        for i in range(total_samples):
            t = i / cls.SAMPLE_RATE
            # Envelope
            if t < attack_s:
                env = t / attack_s
            else:
                elapsed_decay = t - attack_s
                decay_length = duration_s - attack_s
                env = math.exp(-3.0 * elapsed_decay / max(0.01, decay_length))

            val = 0.0
            for mult, weight in harmonics:
                val += math.sin(2.0 * math.pi * (freq * mult) * t) * weight

            samples.append(val * env * 0.7)
        return samples

    @classmethod
    def _create_wake_up(cls) -> List[float]:
        """Rising 2-tone bell chime: C5 (523Hz) -> G5 (784Hz)."""
        c5 = cls._tone(523.25, 0.14, attack_s=0.008, decay_s=0.12)
        g5 = cls._tone(783.99, 0.28, attack_s=0.008, decay_s=0.25)
        # Small overlap
        overlap = int(cls.SAMPLE_RATE * 0.03)
        return c5[:-overlap] + [a + b for a, b in zip(c5[-overlap:], g5[:overlap])] + g5[overlap:]

    @classmethod
    def _create_sleep(cls) -> List[float]:
        """Gentle descending lullaby sigh: G4 (392Hz) -> E4 (330Hz) -> C4 (261Hz)."""
        g4 = cls._tone(392.00, 0.18, attack_s=0.02, decay_s=0.15, harmonics=((1.0, 1.0), (2.0, 0.15)))
        e4 = cls._tone(329.63, 0.20, attack_s=0.02, decay_s=0.16, harmonics=((1.0, 1.0), (2.0, 0.15)))
        c4 = cls._tone(261.63, 0.35, attack_s=0.02, decay_s=0.30, harmonics=((1.0, 1.0), (2.0, 0.1)))
        return g4 + e4 + c4

    @classmethod
    def _create_task_complete(cls) -> List[float]:
        """Joyful 4-tone celebration arpeggio: C5 -> E5 -> G5 -> C6."""
        c5 = cls._tone(523.25, 0.12, attack_s=0.005, decay_s=0.10)
        e5 = cls._tone(659.25, 0.12, attack_s=0.005, decay_s=0.10)
        g5 = cls._tone(783.99, 0.14, attack_s=0.005, decay_s=0.12)
        c6 = cls._tone(1046.50, 0.36, attack_s=0.005, decay_s=0.32, harmonics=((1.0, 1.0), (2.0, 0.35), (3.0, 0.15)))
        return c5 + e5 + g5 + c6

    @classmethod
    def _create_task_notify(cls) -> List[float]:
        """Crisp marimba bubble pop: F5 (698Hz) -> A5 (880Hz)."""
        f5 = cls._tone(698.46, 0.08, attack_s=0.003, decay_s=0.07, harmonics=((1.0, 1.0), (3.0, 0.2)))
        a5 = cls._tone(880.00, 0.16, attack_s=0.003, decay_s=0.14, harmonics=((1.0, 1.0), (3.0, 0.15)))
        return f5 + a5

    @classmethod
    def _create_task_cancel(cls) -> List[float]:
        """Soft mellow low tone: E4 -> C4."""
        e4 = cls._tone(329.63, 0.10, attack_s=0.01, decay_s=0.08)
        c4 = cls._tone(261.63, 0.18, attack_s=0.01, decay_s=0.15)
        return e4 + c4

    @classmethod
    def _create_work_log(cls) -> List[float]:
        """Subtle mechanical typewriter focus click (35ms)."""
        total = int(cls.SAMPLE_RATE * 0.035)
        samples = []
        for i in range(total):
            t = i / cls.SAMPLE_RATE
            env = math.exp(-60.0 * t)
            # High frequency click + low tap
            click = math.sin(2.0 * math.pi * 1200.0 * t) * 0.6 + math.sin(2.0 * math.pi * 440.0 * t) * 0.4
            samples.append(click * env * 0.5)
        return samples

    @classmethod
    def _create_mascot_poke(cls) -> List[float]:
        """Cute, gentle squeak / bubble pop with slight pitch bend."""
        total = int(cls.SAMPLE_RATE * 0.09)
        samples = []
        for i in range(total):
            t = i / cls.SAMPLE_RATE
            env = math.exp(-25.0 * t)
            # Frequency bends from 750Hz up to 920Hz and down to 600Hz
            freq = 750.0 + 300.0 * math.sin(math.pi * t / 0.09)
            val = math.sin(2.0 * math.pi * freq * t)
            samples.append(val * env * 0.55)
        return samples

    @classmethod
    def _create_mascot_drag_start(cls) -> List[float]:
        """Subtle flutter whoosh on drag pickup."""
        total = int(cls.SAMPLE_RATE * 0.08)
        samples = []
        for i in range(total):
            t = i / cls.SAMPLE_RATE
            env = math.sin(math.pi * t / 0.08)
            freq = 300.0 + 400.0 * (t / 0.08)
            val = math.sin(2.0 * math.pi * freq * t)
            samples.append(val * env * 0.35)
        return samples

    @classmethod
    def _create_mascot_drag_end(cls) -> List[float]:
        """Pillowy soft landing tap on drop."""
        total = int(cls.SAMPLE_RATE * 0.07)
        samples = []
        for i in range(total):
            t = i / cls.SAMPLE_RATE
            env = math.exp(-40.0 * t)
            val = math.sin(2.0 * math.pi * 220.0 * t) * 0.7 + math.sin(2.0 * math.pi * 110.0 * t) * 0.3
            samples.append(val * env * 0.4)
        return samples


class SoundManager(QObject):
    """
    Manages low-latency playback of Wiz companion sound effects via QSoundEffect.
    Respects global volume and mute configurations.
    """

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._effects: Dict[str, QSoundEffect] = {}
        self._sounds_dir = config.assets_dir / "sounds"
        self._initialized = False

    def initialize(self) -> None:
        """Synthesize WAV assets and preload QSoundEffect instances."""
        if self._initialized:
            return

        try:
            sound_paths = WavSynthesizer.generate_all(self._sounds_dir)
            vol = config.sound_volume

            for name, path in sound_paths.items():
                effect = QSoundEffect(self)
                effect.setSource(QUrl.fromLocalFile(str(path)))
                effect.setVolume(vol)
                self._effects[name] = effect

            self._initialized = True
        except Exception as e:
            print(f"[SoundManager] Warning: Failed to initialize sound effects: {e}")

    def play(self, sound_name: str) -> None:
        """Play sound effect if sound effects are enabled."""
        if not config.sound_effects_enabled:
            return

        if not self._initialized:
            self.initialize()

        effect = self._effects.get(sound_name)
        if effect:
            try:
                effect.setVolume(config.sound_volume)
                effect.play()
            except Exception as e:
                print(f"[SoundManager] Error playing {sound_name}: {e}")

    def play_wake(self) -> None:
        """Play companion wake-up chime."""
        self.play("wake_up")

    def play_sleep(self) -> None:
        """Play companion sleep lullaby."""
        self.play("sleep")

    def play_task_complete(self) -> None:
        """Play task completion celebration chime."""
        self.play("task_complete")

    def play_task_notify(self) -> None:
        """Play task action notification pop."""
        self.play("task_notify")

    def play_task_cancel(self) -> None:
        """Play task cancellation tone."""
        self.play("task_cancel")

    def play_window_open(self) -> None:
        """Play soft opening tone when a window or popup opens."""
        self.play("task_notify")

    def play_window_close(self) -> None:
        """Play soft dismiss tone when a window or popup closes."""
        self.play("task_cancel")

    def play_work_log(self) -> None:
        """Play activity logging focus tick."""
        self.play("work_log")

    def play_mascot_poke(self) -> None:
        """Play mascot poke / click squeak."""
        self.play("mascot_poke")

    def play_mascot_drag_start(self) -> None:
        """Play mascot drag pickup flutter."""
        self.play("mascot_drag_start")

    def play_mascot_drag_end(self) -> None:
        """Play mascot drop tap."""
        self.play("mascot_drag_end")

    def update_volume(self, volume: float) -> None:
        """Update playback volume across all sound effects."""
        config.set_sound_volume(volume)
        for effect in self._effects.values():
            effect.setVolume(config.sound_volume)

    def set_enabled(self, enabled: bool) -> None:
        """Update enabled state."""
        config.set_sound_effects_enabled(enabled)


# Global singleton instance
sound_manager = SoundManager()
