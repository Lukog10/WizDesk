"""Unit tests for SideNavBar, SettingsView, and 920x680 Widescreen Shell."""

from datetime import date
import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from wiz.core.config import config
from wiz.core.state_machine import StateMachine
from wiz.storage.db import Database
from wiz.storage.models import StorageRepository
from wiz.ui.popup_dialog import QuickEntryDialog
from wiz.ui.sidebar_widget import SideNavBar, NavPillButton
from wiz.ui.settings_view import SettingsView, SettingsCheckbox
from wiz.ui.help_faq_view import HelpFaqView, FaqItemWidget


@pytest.fixture
def repo(tmp_path):
    """Temporary storage repository."""
    db_file = tmp_path / "test_sidebar_shell.db"
    return StorageRepository(Database(db_file))


@pytest.fixture(autouse=True)
def reset_config():
    old_theme = config.theme
    old_vault = config.get("obsidian_vault_path", "")
    old_anim = config.get("enable_floating_animation", True)
    old_interval = config.get("tracking_interval_seconds", 300)
    yield
    config.set_theme(old_theme)
    config.set("obsidian_vault_path", old_vault)
    config.set("enable_floating_animation", old_anim)
    config.set("tracking_interval_seconds", old_interval)


def test_sidebar_nav_pill_button(qapp):
    """Test NavPillButton state, active border, badge counter, and theme switching."""
    pill = NavPillButton(
        mode_id="tasks",
        label="Tasks",
        icon_type="tasks",
        badge_count=0,
        is_dark=True,
    )
    assert pill.mode_id == "tasks"
    assert pill.label == "Tasks"
    assert not pill.is_active

    # Activate
    pill.set_active(True)
    assert pill.is_active

    # Badge counter
    pill.set_badge_count(7)
    assert pill.badge_count == 7

    # Theme
    pill.set_theme(is_dark=False)
    assert not pill.is_dark

    # Click emission
    emitted = []
    pill.mode_selected.connect(lambda m: emitted.append(m))
    pill.click()
    assert emitted == ["tasks"]


def test_sidebar_widget_modes_and_signals(qapp):
    """Test SideNavBar mode switching, theme requests, and badge updates."""
    sidebar = SideNavBar(is_dark=True)
    assert sidebar.current_mode == "tasks"
    assert "tasks" in sidebar.pills
    assert "notes" in sidebar.pills
    assert "activity" in sidebar.pills
    assert "projects" in sidebar.pills
    assert "settings" in sidebar.pills
    assert "help" in sidebar.pills

    # Check initial active state
    assert sidebar.pills["tasks"].is_active
    assert not sidebar.pills["projects"].is_active

    # Mode changed signal
    emitted_modes = []
    sidebar.mode_changed.connect(lambda m: emitted_modes.append(m))

    # Click projects pill
    sidebar.pills["projects"].click()
    assert sidebar.current_mode == "projects"
    assert sidebar.pills["projects"].is_active
    assert not sidebar.pills["tasks"].is_active
    assert emitted_modes == ["projects"]

    # Test settings pill
    sidebar.pills["settings"].click()
    assert sidebar.current_mode == "settings"
    assert sidebar.pills["settings"].is_active
    assert emitted_modes == ["projects", "settings"]

    # Test help pill
    sidebar.pills["help"].click()
    assert sidebar.current_mode == "help"
    assert sidebar.pills["help"].is_active
    assert emitted_modes == ["projects", "settings", "help"]

    # Test tasks badge
    sidebar.set_tasks_badge(4)
    assert sidebar.pills["tasks"].badge_count == 4

    # Theme toggle signal
    theme_requested = []
    sidebar.theme_toggle_requested.connect(lambda: theme_requested.append(True))
    sidebar.theme_btn.click()
    assert len(theme_requested) == 1

    # Theme change
    sidebar.set_theme(is_dark=False)
    assert not sidebar.is_dark
    assert not sidebar.pills["tasks"].is_dark


def test_settings_view_lifecycle_and_saving(qapp, repo: StorageRepository):
    """Test SettingsView preference management and database synchronization."""
    view = SettingsView(repository=repo, is_dark=True)

    # Initial state
    assert hasattr(view, "vault_path_input")
    assert hasattr(view, "float_anim_check")
    assert hasattr(view, "interval_spin")
    assert hasattr(view, "proj_table")
    assert hasattr(view, "save_btn")

    # Modify preferences
    view.vault_path_input.setText("C:/Users/Tester/ObsidianVault")
    view.float_anim_check.setChecked(False)
    view.interval_spin.setValue(15)

    # Save
    saved_signal = []
    view.saved.connect(lambda: saved_signal.append(True))
    view.save_settings()

    assert len(saved_signal) == 1
    assert config.get("obsidian_vault_path") == "C:/Users/Tester/ObsidianVault"
    assert config.get("enable_floating_animation") is False
    assert config.get("tracking_interval_seconds") == 900

    # Test theme toggle on view
    view.set_theme(is_dark=False)
    assert not view.is_dark


def test_quick_entry_dialog_widescreen_and_sidebar_integration(qapp, repo: StorageRepository):
    """Test QuickEntryDialog widescreen 920x680 geometry, sidebar navigation, and 5 views."""
    sm = StateMachine()
    dialog = QuickEntryDialog(sm, repository=repo)

    # Check widescreen window geometry
    assert dialog.width() == 920
    assert dialog.height() >= 560

    # Check Left Side Navigation Bar presence
    assert hasattr(dialog, "sidebar")
    assert isinstance(dialog.sidebar, SideNavBar)
    assert dialog.sidebar.width() == 190

    # Check 6 views in stack
    assert dialog.stack.count() == 6
    assert dialog.stack.widget(0) == dialog.tasks_page
    assert dialog.stack.widget(1) == dialog.notes_page
    assert dialog.stack.widget(2) == dialog.timeline_view
    assert dialog.stack.widget(3) == dialog.project_dashboard_view
    assert dialog.stack.widget(4) == dialog.settings_view
    assert dialog.stack.widget(5) == dialog.help_faq_view

    # Initial view is Tasks
    assert dialog.current_view_mode == "tasks"
    assert dialog.page_title_lbl.text() == "Tasks & To-Dos"
    assert dialog.sidebar.current_mode == "tasks"

    # Switch to Quick Notes via sidebar pill
    dialog.sidebar.pills["notes"].click()
    assert dialog.current_view_mode == "notes"
    assert dialog.page_title_lbl.text() == "Quick Notes"
    assert dialog.stack.currentWidget() == dialog.notes_page

    # Switch to Activity Timeline via sidebar pill
    dialog.sidebar.pills["activity"].click()
    assert dialog.current_view_mode == "activity"
    assert dialog.page_title_lbl.text() == "Activity Timeline"
    assert dialog.stack.currentWidget() == dialog.timeline_view

    # Switch to Projects Dashboard via sidebar pill
    dialog.sidebar.pills["projects"].click()
    assert dialog.current_view_mode == "projects"
    assert dialog.page_title_lbl.text() == "Projects Dashboard"
    assert dialog.stack.currentWidget() == dialog.project_dashboard_view
    assert dialog.date_header_container.isHidden()

    # Switch to Settings via sidebar pill
    dialog.sidebar.pills["settings"].click()
    assert dialog.current_view_mode == "settings"
    assert dialog.page_title_lbl.text() == "Settings & Preferences"
    assert dialog.stack.currentWidget() == dialog.settings_view
    assert dialog.date_header_container.isHidden()

    # Switch to Help & FAQ via sidebar pill
    dialog.sidebar.pills["help"].click()
    assert dialog.current_view_mode == "help"
    assert dialog.page_title_lbl.text() == "Help & Documentation"
    assert dialog.stack.currentWidget() == dialog.help_faq_view
    assert dialog.date_header_container.isHidden()

    # Switch back to Tasks
    dialog.sidebar.pills["tasks"].click()
    assert dialog.current_view_mode == "tasks"
    assert dialog.page_title_lbl.text() == "Tasks & To-Dos"
    assert not dialog.date_header_container.isHidden()

    # Theme toggle on dialog updates sidebar
    dialog.apply_theme("light")
    assert not dialog.is_dark
    assert not dialog.sidebar.is_dark

    dialog.apply_theme("dark")
    assert dialog.is_dark
    assert dialog.sidebar.is_dark

    dialog.close()


def test_help_faq_view_lifecycle(qapp):
    """Test HelpFaqView shortcut customization, saving, reset, and FAQ accordion."""
    view = HelpFaqView(is_dark=True)

    # Check hotkey input fields
    assert "hotkey_workspace" in view.hotkey_inputs
    assert "hotkey_toggle_mascot" in view.hotkey_inputs
    assert "hotkey_quick_task" in view.hotkey_inputs
    assert "hotkey_quick_note" in view.hotkey_inputs

    # Check FAQ items populated
    assert len(view.faq_items) >= 4
    first_faq = view.faq_items[0]
    assert not first_faq.is_expanded
    assert first_faq.a_lbl.isHidden()

    # Test expanding FAQ accordion
    first_faq.header_btn.click()
    assert first_faq.is_expanded
    assert not first_faq.a_lbl.isHidden()
    assert first_faq.indicator_lbl.text() == "[-]"

    # Test custom hotkey input and saving
    view.hotkey_inputs["hotkey_quick_task"].setText("Ctrl+Alt+T")
    view.save_hk_btn.click()

    assert config.get("hotkey_quick_task") == "<ctrl>+<alt>+t"
    assert "successfully" in view.hk_feedback_lbl.text()

    # Test reset to defaults
    view.reset_hk_btn.click()
    assert config.get("hotkey_quick_task") == "<ctrl>+<shift>+t"
    assert config.get("hotkey_workspace") == "<ctrl>+<shift>+w"
    assert "default" in view.hk_feedback_lbl.text()

    # Test theme toggle
    view.set_theme(is_dark=False)
    assert not view.is_dark
    view.set_theme(is_dark=True)
    assert view.is_dark
