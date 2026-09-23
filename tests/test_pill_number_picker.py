"""
Unit tests for PillNumberPicker, DurationPillSelector, and PillSpinBox components.
"""

import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from wiz.ui.pill_number_picker import NumberPill, DurationPillSelector, PillSpinBox


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def test_number_pill_basic(qapp):
    pill = NumberPill(unit="min", min_val=1, max_val=120, default_val=5, is_dark=True)
    assert pill.value() == 5
    assert pill.input_edit.text() == "5"
    assert pill.unit_lbl.text() == "min"
    assert pill.height() == 30

    # Set value
    pill.setValue(15)
    assert pill.value() == 15
    assert pill.input_edit.text() == "15"

    # Clamping
    pill.setValue(200)
    assert pill.value() == 120

    pill.setValue(0)
    assert pill.value() == 1

    # Theme toggle
    pill.set_theme(False)
    assert pill.is_dark is False
    pill.set_theme(True)
    assert pill.is_dark is True


def test_duration_pill_selector(qapp):
    selector = DurationPillSelector(min_minutes=1, max_minutes=720, default_minutes=5, is_dark=True)
    assert selector.value() == 5
    assert selector.height() == 30
    assert selector.unit_lbl.text() == "min"

    # Set new duration
    selector.setValue(30)
    assert selector.value() == 30

    # Theme toggling
    selector.set_theme(False)
    assert selector.is_dark is False
    selector.set_theme(True)
    assert selector.is_dark is True


def test_pill_spin_box(qapp):
    box = PillSpinBox(min_val=1, max_val=30, default_val=5, unit="snapshots", is_dark=True)
    assert box.value() == 5
    assert box.height() == 30
    assert box.unit_lbl.text() == "snapshots"

    box.setValue(12)
    assert box.value() == 12

    # Suffix changes
    box.setSuffix(" backups")
    assert box.unit_lbl.text() == "backups"

    # Theme toggle
    box.set_theme(False)
    assert box.is_dark is False
    box.set_theme(True)
    assert box.is_dark is True
