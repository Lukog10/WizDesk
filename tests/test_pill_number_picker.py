"""
Unit tests for PillNumberPicker, DurationPillSelector, and PillSpinBox components.
"""

import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from wiz.ui.pill_number_picker import CheckButton, NumberPill, DurationPillSelector, PillSpinBox


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def test_number_pill_basic(qapp):
    pill = NumberPill(unit="Hr.", min_val=0, max_val=24, default_val=2, is_dark=True)
    assert pill.value() == 2
    assert pill.input_edit.text() == "2"
    assert pill.unit_lbl.text() == "Hr."

    # Set value
    pill.setValue(5)
    assert pill.value() == 5
    assert pill.input_edit.text() == "5"

    # Clamping
    pill.setValue(100)
    assert pill.value() == 24

    pill.setValue(-10)
    assert pill.value() == 0

    # Theme toggle
    pill.set_theme(False)
    assert pill.is_dark is False
    pill.set_theme(True)
    assert pill.is_dark is True


def test_duration_pill_selector(qapp):
    selector = DurationPillSelector(min_minutes=1, max_minutes=720, default_minutes=5, is_dark=True)
    assert selector.value() == 5
    assert selector.hr_pill.value() == 0
    assert selector.min_pill.value() == 5

    # Change to 2 Hr 30 Min (150 minutes, matching user reference image)
    selector.setValue(150)
    assert selector.value() == 150
    assert selector.hr_pill.value() == 2
    assert selector.min_pill.value() == 30

    # Test sub-pill edits
    selector.hr_pill.setValue(1)
    selector.min_pill.setValue(45)
    assert selector.value() == 105

    # Test confirmation click
    confirmed_values = []
    selector.confirmed.connect(lambda v: confirmed_values.append(v))
    selector.check_btn.click()
    assert len(confirmed_values) == 1
    assert confirmed_values[0] == 105

    # Theme toggling
    selector.set_theme(False)
    assert selector.is_dark is False
    selector.set_theme(True)
    assert selector.is_dark is True


def test_pill_spin_box(qapp):
    box = PillSpinBox(min_val=1, max_val=30, default_val=5, unit="snapshots", is_dark=True)
    assert box.value() == 5
    assert box.pill.unit_lbl.text() == "snapshots"

    box.setValue(12)
    assert box.value() == 12

    # Suffix changes
    box.setSuffix(" backups")
    assert box.pill.unit_lbl.text() == "backups"

    # Confirmation
    confirmed = []
    box.confirmed.connect(lambda v: confirmed.append(v))
    box.check_btn.click()
    assert len(confirmed) == 1
    assert confirmed[0] == 12

    # Theme toggle
    box.set_theme(False)
    assert box.is_dark is False
    box.set_theme(True)
    assert box.is_dark is True
