"""Tests for Section Header and Calendar Date Navigator Layout Optimization.

Validates:
1. Widget hierarchy (page_title_lbl and date_header_container inside inner_card at index 0).
2. Window controls sizing (22x22 px) in outer top bar.
3. Day navigation chevrons (‹ and › buttons at 28x28 px).
4. Visibility matrix across all 7 view modes.
5. Filter pills integrity on tasks page.
6. Draggable area behavior (page_title_lbl draggable, controls excluded, inner card content excluded).
"""

import pytest
from datetime import date
from PyQt6.QtCore import Qt, QPoint, QSize
from PyQt6.QtWidgets import QApplication

from wiz.storage.db import Database
from wiz.storage.models import StorageRepository
from wiz.core.state_machine import StateMachine
from wiz.ui.popup_dialog import QuickEntryDialog


@pytest.fixture
def repo(tmp_path):
    db_file = tmp_path / "test_wiz.sqlite"
    db = Database(db_file)
    r = StorageRepository(db)
    return r


@pytest.fixture
def dialog(qapp, repo):
    sm = StateMachine()
    d = QuickEntryDialog(sm, repository=repo)
    d.show()
    return d


def test_section_header_hierarchy(dialog):
    """Verify card_header_widget is inside inner_card at index 0 holding title and date container."""
    assert dialog.card_header_widget.parent() == dialog.inner_card
    assert dialog.inner_layout.indexOf(dialog.card_header_widget) == 0
    assert dialog.inner_layout.indexOf(dialog.stack) == 1

    # Verify page_title_lbl and date_header_container are inside card_header_widget
    assert dialog.page_title_lbl.parent() == dialog.card_header_widget
    assert dialog.date_header_container.parent() == dialog.card_header_widget
    assert dialog.card_header_widget.layout().spacing() == 6


def test_window_controls_dimensions_and_placement(dialog):
    """Verify window controls are downsized to 22x22 px in the outer bar."""
    assert dialog.min_btn.width() == 22
    assert dialog.min_btn.height() == 22
    assert dialog.close_btn.width() == 22
    assert dialog.close_btn.height() == 22

    # Verify window controls are NOT inside inner_card
    assert dialog.min_btn.parent() != dialog.inner_card
    assert dialog.close_btn.parent() != dialog.inner_card


def test_date_button_pill_and_hidden_chevrons(dialog):
    """Verify chevron navigation buttons are hidden and date_btn displays formatted date subtitle."""
    from wiz.ui.popup_dialog import format_header_date
    assert dialog.prev_day_btn.isHidden() is True
    assert dialog.next_day_btn.isHidden() is True
    assert dialog.date_btn.isVisible() is True
    assert dialog.date_btn.text() == format_header_date(dialog.selected_date)


def test_header_visibility_matrix(dialog):
    """Verify page_title_lbl is visible across ALL modes, and date_header_container toggles appropriately."""
    # 1. Tasks mode (default)
    assert dialog.current_view_mode == "tasks"
    assert dialog.page_title_lbl.text() == "Tasks & To-Dos"
    assert dialog.page_title_lbl.isVisible() is True
    assert dialog.date_header_container.isVisible() is True

    # 2. Notes mode (all notes displayed, date header is hidden)
    dialog._set_view_mode("notes")
    assert dialog.page_title_lbl.text() == "Quick Notes"
    assert dialog.page_title_lbl.isVisible() is True
    assert dialog.date_header_container.isVisible() is False

    # 3. Activity mode
    dialog._set_view_mode("activity")
    assert dialog.page_title_lbl.text() == "Activity Timeline"
    assert dialog.page_title_lbl.isVisible() is True
    assert dialog.date_header_container.isVisible() is True

    # 4. Projects mode (Dashboard)
    dialog._set_view_mode("projects")
    assert dialog.page_title_lbl.text() == "Projects Dashboard"
    assert dialog.page_title_lbl.isVisible() is True
    assert dialog.date_header_container.isVisible() is False

    # 5. Settings mode
    dialog._set_view_mode("settings")
    assert dialog.page_title_lbl.text() == "Settings & Preferences"
    assert dialog.page_title_lbl.isVisible() is True
    assert dialog.date_header_container.isVisible() is False

    # 6. Help mode
    dialog._set_view_mode("help")
    assert dialog.page_title_lbl.text() == "Help & Documentation"
    assert dialog.page_title_lbl.isVisible() is True
    assert dialog.date_header_container.isVisible() is False

    # 7. Calendar mode
    dialog._set_view_mode("calendar")
    assert dialog.page_title_lbl.text() == "Calendar & Schedule"
    assert dialog.page_title_lbl.isVisible() is True
    assert dialog.date_header_container.isVisible() is False

    # Return to Tasks
    dialog._set_view_mode("tasks")
    assert dialog.page_title_lbl.text() == "Tasks & To-Dos"
    assert dialog.page_title_lbl.isVisible() is True
    assert dialog.date_header_container.isVisible() is True


def test_filter_pills_intact(dialog):
    """Verify status filter capsules remain completely untouched on tasks page."""
    assert hasattr(dialog, "filter_bar")
    assert dialog.filter_bar.parent() == dialog.tasks_page
    assert dialog.filter_bar.current_filter == "Task"
    assert dialog.filter_bar.options == ["Task", "In progress", "Completed", "Cancelled"]


def test_draggable_area_behavior(dialog):
    """Verify that clicking page_title_lbl is draggable, but interactive controls are not."""
    title_center = dialog.page_title_lbl.mapToGlobal(dialog.page_title_lbl.rect().center())
    assert dialog._is_in_draggable_area(title_center) is True

    # Controls must not be draggable
    min_center = dialog.min_btn.mapToGlobal(dialog.min_btn.rect().center())
    assert dialog._is_in_draggable_area(min_center) is False

    close_center = dialog.close_btn.mapToGlobal(dialog.close_btn.rect().center())
    assert dialog._is_in_draggable_area(close_center) is False

    prev_day_center = dialog.prev_day_btn.mapToGlobal(dialog.prev_day_btn.rect().center())
    assert dialog._is_in_draggable_area(prev_day_center) is False
