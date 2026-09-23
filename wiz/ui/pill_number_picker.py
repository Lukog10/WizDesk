"""
Modern Compact Pill Number Picker & Duration Selector for WizDesk.
Matches Untitled UI 30px button dimensions with rounded corners (border-radius: 6px),
bold numbers, secondary unit labels, and seamless mouse wheel / arrow navigation.
"""

from typing import Optional
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import (
    QFont,
    QColor,
    QCursor,
    QWheelEvent,
    QKeyEvent,
    QIntValidator,
)
from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QFrame,
)

from wiz.ui.fonts import FONT_SANS, get_font


class NumberPill(QFrame):
    """
    Compact rounded pill container with an editable bold number and secondary unit text.
    Height: 30px, border-radius: 6px (matching Untitled UI action buttons).
    Supports keyboard arrows, mouse wheel scrolling, and direct numeric typing.
    """

    valueChanged = pyqtSignal(int)
    confirmed = pyqtSignal(int)
    editingFinished = pyqtSignal()

    def __init__(
        self,
        unit: str,
        min_val: int = 1,
        max_val: int = 999,
        default_val: int = 5,
        is_dark: bool = True,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.unit_text = unit
        self.min_val = min_val
        self.max_val = max_val
        self._value = default_val
        self.is_dark = is_dark

        self._init_ui()
        self.setValue(default_val)

    def _init_ui(self) -> None:
        self.setFixedHeight(30)
        self.setCursor(QCursor(Qt.CursorShape.IBeamCursor))

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 2, 10, 2)
        layout.setSpacing(4)

        # 1. Numeric Editor
        self.input_edit = QLineEdit(self)
        self.input_edit.setFont(get_font(11, QFont.Weight.Bold))
        self.input_edit.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.input_edit.setValidator(QIntValidator(self.min_val, self.max_val, self))
        self.input_edit.setFrame(False)
        self.input_edit.setAttribute(Qt.WidgetAttribute.WA_MacShowFocusRect, False)
        self.input_edit.editingFinished.connect(self._on_editing_finished)
        self.input_edit.textEdited.connect(self._on_text_edited)
        layout.addWidget(self.input_edit, stretch=1)

        # 2. Unit Label
        self.unit_lbl = QLabel(self.unit_text, self)
        self.unit_lbl.setFont(get_font(11, QFont.Weight.Medium))
        self.unit_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.unit_lbl, stretch=1)

        self._update_width()
        self._apply_styling()

    def _update_width(self) -> None:
        text_len = len(self.unit_text)
        if text_len <= 3:
            self.setFixedWidth(72)
        elif text_len <= 5:
            self.setFixedWidth(80)
        elif text_len <= 9:
            self.setFixedWidth(116)
        else:
            self.setFixedWidth(128)

    def value(self) -> int:
        return self._value

    def setValue(self, val: int) -> None:
        clamped = max(self.min_val, min(self.max_val, int(val)))
        if clamped != self._value or self.input_edit.text() != str(clamped):
            self._value = clamped
            self.input_edit.setText(str(clamped))
            self.valueChanged.emit(clamped)
            self.confirmed.emit(clamped)

    def setRange(self, min_val: int, max_val: int) -> None:
        self.min_val = min_val
        self.max_val = max_val
        self.input_edit.setValidator(QIntValidator(self.min_val, self.max_val, self))
        self.setValue(self._value)

    def set_unit(self, unit: str) -> None:
        self.unit_text = unit
        self.unit_lbl.setText(unit)
        self._update_width()

    def setSuffix(self, suffix: str) -> None:
        clean = suffix.strip()
        if clean:
            self.set_unit(clean)

    def set_theme(self, is_dark: bool) -> None:
        self.is_dark = is_dark
        self._apply_styling()

    def setStyleSheet(self, qss: str) -> None:
        # Prevent generic input_qss from overriding pill border-radius and layout
        pass

    def _on_text_edited(self, text: str) -> None:
        if text.strip().isdigit():
            val = int(text.strip())
            clamped = max(self.min_val, min(self.max_val, val))
            self._value = clamped
            self.valueChanged.emit(clamped)
            self.confirmed.emit(clamped)

    def _on_editing_finished(self) -> None:
        raw = self.input_edit.text().strip()
        val = int(raw) if raw.isdigit() else self.min_val
        self.setValue(val)
        self.editingFinished.emit()

    def wheelEvent(self, event: QWheelEvent) -> None:
        delta = event.angleDelta().y()
        step = 1
        if delta > 0:
            self.setValue(self._value + step)
        elif delta < 0:
            self.setValue(self._value - step)
        event.accept()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Up:
            self.setValue(self._value + 1)
            event.accept()
        elif event.key() == Qt.Key.Key_Down:
            self.setValue(self._value - 1)
            event.accept()
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.clearFocus()
            self.input_edit.clearFocus()
            self._on_editing_finished()
            event.accept()
        else:
            super().keyPressEvent(event)

    def mousePressEvent(self, event) -> None:
        self.input_edit.setFocus()
        self.input_edit.selectAll()
        super().mousePressEvent(event)

    def _apply_styling(self) -> None:
        bg_color = "#27272A" if self.is_dark else "#EBE6DC"
        border_color = "#3F3F46" if self.is_dark else "#D6D0C5"
        text_primary = "#F4F4F5" if self.is_dark else "#242220"
        text_secondary = "#A1A1AA" if self.is_dark else "#78716C"
        focus_border = "#C2410C" if self.is_dark else "#BA3F1A"

        super().setStyleSheet(f"""
            NumberPill {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 6px;
            }}
            NumberPill:hover {{
                border-color: {focus_border};
            }}
        """)

        self.input_edit.setStyleSheet(f"""
            QLineEdit {{
                background: transparent;
                border: none;
                color: {text_primary};
                font-family: {FONT_SANS};
                font-size: 11px;
                font-weight: 700;
                padding: 0;
            }}
        """)

        self.unit_lbl.setStyleSheet(f"""
            QLabel {{
                background: transparent;
                border: none;
                color: {text_secondary};
                font-family: {FONT_SANS};
                font-size: 11px;
                font-weight: 500;
                padding-left: 2px;
            }}
        """)


class DurationPillSelector(NumberPill):
    """
    Compact single-pill duration picker for minutes [ 5 min ],
    matching the Untitled UI 30px button dimensions.
    Drop-in compatible with QSpinBox API (.value(), .setValue(), .setRange(), .valueChanged).
    """

    def __init__(
        self,
        min_minutes: int = 1,
        max_minutes: int = 720,
        default_minutes: int = 5,
        is_dark: bool = True,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(
            unit="min",
            min_val=min_minutes,
            max_val=max_minutes,
            default_val=default_minutes,
            is_dark=is_dark,
            parent=parent,
        )


class PillSpinBox(NumberPill):
    """
    Compact single-pill number picker [ 5 snapshots ],
    matching the Untitled UI 30px button dimensions.
    Drop-in compatible with QSpinBox API (.value(), .setValue(), .setRange(), .setSuffix()).
    """

    def __init__(
        self,
        min_val: int = 1,
        max_val: int = 100,
        default_val: int = 5,
        unit: str = "snapshots",
        is_dark: bool = True,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(
            unit=unit,
            min_val=min_val,
            max_val=max_val,
            default_val=default_val,
            is_dark=is_dark,
            parent=parent,
        )
