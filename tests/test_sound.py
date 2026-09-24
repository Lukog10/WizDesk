"""Tests for procedural sound synthesis and SoundManager."""

import pytest
from pathlib import Path
from wiz.core.config import config
from wiz.core.sound import WavSynthesizer, SoundManager


def test_wav_synthesizer_generates_valid_files(tmp_path: Path):
    """Verify that WavSynthesizer produces non-empty, readable WAV files for all sounds."""
    sound_map = WavSynthesizer.generate_all(tmp_path)
    expected_sounds = [
        "wake_up", "sleep", "task_complete", "task_notify",
        "task_cancel", "work_log", "mascot_poke",
        "mascot_drag_start", "mascot_drag_end"
    ]
    for sound in expected_sounds:
        assert sound in sound_map
        p = sound_map[sound]
        assert p.exists()
        assert p.stat().st_size > 1000  # Non-trivial audio file


def test_sound_manager_volume_and_mute(qapp):
    """Verify that volume updates and mute states are respected."""
    sm = SoundManager()
    
    # Test volume clamping
    config.set_sound_volume(0.8)
    assert config.sound_volume == 0.8
    config.set_sound_volume(1.5)  # Should clamp to 1.0
    assert config.sound_volume == 1.0
    config.set_sound_volume(-0.5)  # Should clamp to 0.0
    assert config.sound_volume == 0.0

    # Reset to normal
    config.set_sound_volume(0.65)
    assert config.sound_volume == 0.65

    # Test mute
    config.set_sound_effects_enabled(False)
    assert not config.sound_effects_enabled
    # When disabled, calling play should do nothing and not raise
    sm.play_wake()
    sm.play_task_complete()

    # Re-enable
    config.set_sound_effects_enabled(True)
    assert config.sound_effects_enabled


def test_sound_manager_methods_exist(qapp):
    """Verify that all helper playback methods exist and run safely."""
    sm = SoundManager()
    methods = [
        sm.play_wake,
        sm.play_sleep,
        sm.play_task_complete,
        sm.play_task_notify,
        sm.play_task_cancel,
        sm.play_work_log,
        sm.play_mascot_poke,
        sm.play_mascot_drag_start,
        sm.play_mascot_drag_end,
        sm.play_state_wake,
        sm.play_state_sleep,
        sm.play_state_working,
        sm.play_chime,
        sm.play_task_add,
        sm.play_task_delete,
    ]
    for method in methods:
        assert callable(method)
        # Verify calling does not crash
        method()
