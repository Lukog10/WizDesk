"""Unit tests for SideNavBar, SettingsView, and 920x680 Widescreen Shell."""

from datetime import date
import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from wiz.core.config import config
from wiz.core.state_machine import StateMachine
from wiz.storage.db import Database
from wiz.storage.models import StorageRepository
from wiz.ui.popup_dialog import QuickEntryDialog, SegmentedFilterBar
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
    old_sidebar = config.sidebar_collapsed
    config.set_sidebar_collapsed(False)
    yield
    config.set_theme(old_theme)
    config.set("obsidian_vault_path", old_vault)
    config.set("enable_floating_animation", old_anim)
    config.set("tracking_interval_seconds", old_interval)
    config.set_sidebar_collapsed(old_sidebar)


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
    assert "calendar" in sidebar.pills
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
    """Test SettingsView preference management, categories, and database synchronization."""
    view = SettingsView(repository=repo, is_dark=True)

    # Initial state
    assert hasattr(view, "vault_path_input")
    assert hasattr(view, "float_anim_check")
    assert hasattr(view, "always_on_top_check")
    assert hasattr(view, "autostart_check")
    assert hasattr(view, "sound_check")
    assert hasattr(view, "vault_logs_folder_input")
    assert hasattr(view, "interval_spin")
    assert hasattr(view, "proj_table")
    assert hasattr(view, "save_btn")
    assert hasattr(view, "category_bar")

    # Verify category navigation
    assert view.stack.currentIndex() == 0  # General
    view.category_bar.buttons["hotkeys"].click()
    assert view.stack.currentIndex() == 1
    view.category_bar.buttons["projects"].click()
    assert view.stack.currentIndex() == 2
    view.category_bar.buttons["integrations"].click()
    assert view.stack.currentIndex() == 3
    view.category_bar.buttons["general"].click()
    assert view.stack.currentIndex() == 0

    # Modify preferences across tabs
    view.vault_path_input.setText("C:/Users/Tester/ObsidianVault")
    view.vault_logs_folder_input.setText("Custom Vault Logs")
    view.float_anim_check.setChecked(False)
    view.always_on_top_check.setChecked(False)
    view.autostart_check.setChecked(True)
    view.sound_check.setChecked(True)
    view.interval_spin.setValue(15)

    # Modify hotkey inside SettingsView
    assert "hotkey_quick_task" in view.hotkey_inputs
    view.hotkey_inputs["hotkey_quick_task"].setText("Ctrl+Alt+K")

    # Save
    saved_signal = []
    view.saved.connect(lambda: saved_signal.append(True))
    view.save_settings()

    assert len(saved_signal) == 1
    assert config.get("obsidian_vault_path") == "C:/Users/Tester/ObsidianVault"
    assert config.get("obsidian_logs_folder") == "Custom Vault Logs"
    assert config.get("enable_floating_animation") is False
    assert config.get("always_on_top") is False
    assert config.get("auto_start_on_login") is True
    assert config.get("sound_effects") is True
    assert config.get("tracking_interval_seconds") == 900
    assert config.get("hotkey_quick_task") == "<ctrl>+<alt>+k"

    # Test theme toggle on view
    view.set_theme(is_dark=False)
    assert not view.is_dark
    view.set_theme(is_dark=True)
    assert view.is_dark


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

    # Check 7 views in stack
    assert dialog.stack.count() == 7
    assert dialog.stack.widget(0) == dialog.tasks_page
    assert dialog.stack.widget(1) == dialog.notes_page
    assert dialog.stack.widget(2) == dialog.calendar_view
    assert dialog.stack.widget(3) == dialog.timeline_view
    assert dialog.stack.widget(4) == dialog.project_dashboard_view
    assert dialog.stack.widget(5) == dialog.settings_view
    assert dialog.stack.widget(6) == dialog.help_faq_view

    # Initial view is Tasks
    assert dialog.current_view_mode == "tasks"
    assert dialog.page_title_lbl.text() == "Tasks & To-Dos"
    assert dialog.sidebar.current_mode == "tasks"

    # Switch to Calendar via sidebar pill
    dialog.sidebar.pills["calendar"].click()
    assert dialog.current_view_mode == "calendar"
    assert dialog.page_title_lbl.text() == "Calendar & Schedule"
    assert dialog.stack.currentWidget() == dialog.calendar_view
    assert dialog.date_header_container.isHidden()

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
    """Test redesigned HelpFaqView category filtering, accordion expansion, and docs mode."""
    view = HelpFaqView(is_dark=True)

    # Check FAQ items populated
    assert len(view.faq_items) >= 4
    first_faq = view.faq_items[0]
    assert not first_faq.is_expanded
    assert first_faq.a_lbl.isHidden()
    assert first_faq.indicator_lbl.text() == "+"

    # Test expanding FAQ accordion
    first_faq.header_btn.click()
    assert first_faq.is_expanded
    assert not first_faq.a_lbl.isHidden()
    assert first_faq.indicator_lbl.text() == "—"

    # Test collapsing FAQ accordion
    first_faq.header_btn.click()
    assert not first_faq.is_expanded
    assert first_faq.a_lbl.isHidden()
    assert first_faq.indicator_lbl.text() == "+"

    # Test FAQ category filtering
    view.filter_faq_category("mascot")
    assert view.current_faq_cat == "mascot"
    mascot_items = [item for item in view.faq_items if item.category == "mascot"]
    other_items = [item for item in view.faq_items if item.category != "mascot"]
    for item in mascot_items:
        assert not item.isHidden()
    for item in other_items:
        assert item.isHidden()

    # Reset to all
    view.filter_faq_category("all")
    assert view.current_faq_cat == "all"
    for item in view.faq_items:
        assert not item.isHidden()

    # Test Documentation view mode switching
    view.switch_view_mode("docs")
    assert view.current_mode == "docs"
    assert view.stack.currentIndex() == 1
    assert view.tag_pill.text() == "/ DOCS"

    view.switch_view_mode("faq")
    assert view.current_mode == "faq"
    assert view.stack.currentIndex() == 0
    assert view.tag_pill.text() == "/ FAQS"

    # Test theme toggle
    view.set_theme(is_dark=False)
    assert not view.is_dark
    view.set_theme(is_dark=True)
    assert view.is_dark


def test_help_to_settings_navigation(qapp, repo: StorageRepository, monkeypatch):
    """Test clicking GitHub contribute button and documentation shortcut navigation."""
    sm = StateMachine()
    dialog = QuickEntryDialog(sm, repository=repo)

    # Navigate to help page
    dialog.sidebar.pills["help"].click()
    assert dialog.current_view_mode == "help"
    assert dialog.stack.currentWidget() == dialog.help_faq_view

    # Verify contribute box and button exist
    assert hasattr(dialog.help_faq_view, "contribute_box")
    assert hasattr(dialog.help_faq_view, "github_btn")

    opened_urls = []
    from PyQt6.QtGui import QDesktopServices
    monkeypatch.setattr(QDesktopServices, "openUrl", lambda url: opened_urls.append(url.toString()))

    # Click Contribute on GitHub button
    dialog.help_faq_view.github_btn.click()
    assert len(opened_urls) == 1
    assert opened_urls[0] == "https://github.com/Lukog10/WizDesk"

    # Verify documentation Shortcuts topic navigates to settings hotkey category
    dialog.help_faq_view._on_doc_topic_clicked("Shortcuts")
    assert dialog.current_view_mode == "settings"
    assert dialog.stack.currentWidget() == dialog.settings_view
    assert dialog.settings_view.stack.currentIndex() == 1  # Hotkeys tab
    assert dialog.settings_view.category_bar.current_category == "hotkeys"

    dialog.close()


def test_sidebar_collapse_and_workspace_expansion(qapp, repo: StorageRepository):
    """Test sidebar collapsing to 58px, icon-only pills, toggle button, and workspace expansion."""
    sm = StateMachine()
    config.set_sidebar_collapsed(False)
    dialog = QuickEntryDialog(sm, repository=repo)

    assert not dialog.sidebar.is_collapsed
    assert dialog.sidebar.width() == 190
    assert not dialog.sidebar.brand_container.isHidden()
    assert not dialog.sidebar.workspace_lbl.isHidden()

    # Initial workspace width
    initial_sidebar_w = dialog.sidebar.width()
    assert initial_sidebar_w == 190

    # Toggle sidebar via the toggle button
    dialog.sidebar.toggle_btn.click()

    assert dialog.sidebar.is_collapsed
    assert dialog.sidebar.width() == 58
    assert dialog.sidebar.brand_container.isHidden()
    assert dialog.sidebar.workspace_lbl.isHidden()
    assert config.sidebar_collapsed is True

    # Check that each nav pill is collapsed, has tooltip, and is sized 44px
    for m_id, pill in dialog.sidebar.pills.items():
        assert pill.is_collapsed
        assert pill.width() == 44
        assert pill.toolTip() != ""
    assert dialog.sidebar.theme_btn.width() == 44

    # Re-expand sidebar
    dialog.sidebar.toggle_btn.click()
    assert not dialog.sidebar.is_collapsed
    assert dialog.sidebar.width() == 190
    assert not dialog.sidebar.brand_container.isHidden()
    assert not dialog.sidebar.workspace_lbl.isHidden()
    assert config.sidebar_collapsed is False
    for m_id, pill in dialog.sidebar.pills.items():
        assert not pill.is_collapsed
        assert pill.width() == 170
    assert dialog.sidebar.theme_btn.width() == 170

    dialog.close()


def test_task_filter_bar_faq_styling(qapp):
    """Test SegmentedFilterBar styling, options, active tab, and theme switching matching FAQ style."""
    bar = SegmentedFilterBar(is_dark=True)
    assert bar.options == ["Task", "In progress", "Completed", "Cancelled"]
    assert bar.current_filter == "Task"

    # Verify buttons created
    for opt in bar.options:
        assert opt in bar._buttons

    # Switch active filter
    emitted = []
    bar.filter_changed.connect(lambda f: emitted.append(f))
    bar.set_active_filter("In progress")
    assert bar.current_filter == "In progress"
    assert emitted == ["In progress"]

    # Toggle theme
    bar.set_dark_mode(is_dark=False)
    assert not bar.is_dark
    bar.set_dark_mode(is_dark=True)
    assert bar.is_dark


def test_quick_entry_dialog_reuse_and_settings_tabs(qapp, repo: StorageRepository):
    """Verify WizApplication reuses the dialog instance and category bar buttons remain stable."""
    from wiz.__main__ import WizApplication
    from wiz.ui.settings_view import SettingsCategoryBar

    # Test SettingsCategoryBar dimensions and stability
    cat_bar = SettingsCategoryBar(is_dark=True)
    assert cat_bar.height() == 38
    for cat_id in ["general", "hotkeys", "projects", "integrations"]:
        assert cat_id in cat_bar.buttons
        btn = cat_bar.buttons[cat_id]
        assert btn.height() == 30

    cat_bar.set_active_category("hotkeys")
    assert cat_bar.current_category == "hotkeys"
    assert cat_bar.buttons["hotkeys"].height() == 30

    cat_bar.set_theme(is_dark=False)
    assert not cat_bar.is_dark
    assert cat_bar.buttons["general"].height() == 30

    # Test WizApplication dialog reuse
    app_instance = WizApplication()
    assert app_instance._quick_entry_dialog is None

    app_instance.show_quick_entry()
    dlg_ref1 = app_instance._quick_entry_dialog
    assert dlg_ref1 is not None
    assert dlg_ref1.isVisible()

    # Second call must reuse the existing dialog, not instantiate a duplicate
    app_instance.show_quick_entry()
    dlg_ref2 = app_instance._quick_entry_dialog
    assert dlg_ref1 is dlg_ref2

    # show_settings must also reuse the same dialog and switch mode
    app_instance.show_settings()
    assert app_instance._quick_entry_dialog is dlg_ref1
    assert dlg_ref1.current_view_mode == "settings"

    app_instance.quit()

