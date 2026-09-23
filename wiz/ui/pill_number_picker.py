"""
Modern Pill Number Picker & Duration Selector for WizDesk.
Matches the Untitled UI aesthetic with rounded pill containers, bold numbers,
secondary unit labels, mouse wheel / arrow navigation, and interactive check confirmation.
"""

from typing import Optional
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSize, QRectF, QPointF
from PyQt6.QtGui import (
    QFont,
    QColor,
    QCursor,
    QPainter,
    QPen,
    QWheelEvent,
    QKeyEvent,
    QIntValidator,
)
from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QFrame,
    QSizePolicy,
)

from wiz.ui.fonts import FONT_SANS, FONT_MONO, get_font


class CheckButton(QPushButton):
    """
    Square rounded button rendering a crisp vector checkmark with interactive feedback.
    """

    def __init__(self, is_dark: bool = True, size: int = 38, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.is_dark = is_dark
        self.btn_size = size
        self.is_confirmed = False
        self._hovered = False

        self.setFixedSize(size, size)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setToolTip("Confirm / Apply")
        self.clicked.connect(self._on_click)

    def set_theme(self, is_dark: bool) -> None:
        self.is_dark = is_dark
        self.update()

    def _on_click(self) -> None:
        self.is_confirmed = True
        self.update()
        QTimer.singleShot(1100, self._reset_confirmed)

    def _reset_confirmed(self) -> None:
        self.is_confirmed = False
        self.update()

    def enterEvent(self, event) -> None:
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._hovered = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Background and border styling
        if self.is_confirmed:
            bg_color = QColor("#14532D" if self.is_dark else "#DCFCE7")
            border_color = QColor("#16A34A" if self.is_dark else "#86EFAC")
        elif self._hovered:
            bg_color = QColor("#38383E" if self.is_dark else "#E4E4E7")
            border_color = QColor("#52525B" if self.is_dark else "#D4D4D8")
        else:
            bg_color = QColor("#27272A" if self.is_dark else "#F4F4F6")
            border_color = QColor("#3F3F46" if self.is_dark else "#E4E4E7")

        rect = QRectF(0.5, 0.5, self.width() - 1.0, self.height() - 1.0)
        painter.setBrush(bg_color)
        painter.setPen(QPen(border_color, 1.0))
        painter.drawRoundedRect(rect, 11.0, 11.0)

        # Checkmark vector icon
        if self.is_confirmed:
            icon_color = QColor("#22C55E" if self.is_dark else "#16A34A")
        else:
            icon_color = QColor("#F4F4F5" if self.is_dark else "#18181B")

        pen = QPen(icon_color, 2.6)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)

        # Centered checkmark path matching reference design
        cx = float(self.width()) / 2.0
        cy = float(self.height()) / 2.0

        p1 = QPointF(cx - 5.5, cy + 0.5)
        p2 = QPointF(cx - 1.5, cy + 4.5)
        p3 = QPointF(cx + 6.0, cy - 4.0)

        painter.drawLine(p1, p2)
        painter.drawLine(p2, p3)


class NumberPill(QFrame):
    """
    Individual rounded pill container with an editable bold number and secondary unit text.
    Supports keyboard arrows, mouse wheel scrolling, and direct numeric typing.
    """

    valueChanged = pyqtSignal(int)
    editingFinished = pyqtSignal()

    def __init__(
        self,
        unit: str,
        min_val: int = 0,
        max_val: int = 999,
        default_val: int = 0,
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
        self.setFixedHeight(38)
        self.setCursor(QCursor(Qt.CursorShape.IBeamCursor))

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 2, 14, 2)
        layout.setSpacing(6)

        # 1. Numeric Editor
        self.input_edit = QLineEdit(self)
        self.input_edit.setFont(get_font(13, QFont.Weight.Bold))
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

        self._apply_styling()

    def value(self) -> int:
        return self._value

    def setValue(self, val: int) -> None:
        clamped = max(self.min_val, min(self.max_val, int(val)))
        if clamped != self._value or self.input_edit.text() != str(clamped):
            self._value = clamped
            self.input_edit.setText(str(clamped))
            self.valueChanged.emit(clamped)

    def setRange(self, min_val: int, max_val: int) -> None:
        self.min_val = min_val
        self.max_val = max_val
        self.input_edit.setValidator(QIntValidator(self.min_val, self.max_val, self))
        self.setValue(self._value)

    def set_unit(self, unit: str) -> None:
        self.unit_text = unit
        self.unit_lbl.setText(unit)

    def set_theme(self, is_dark: bool) -> None:
        self.is_dark = is_dark
        self._apply_styling()

    def _on_text_edited(self, text: str) -> None:
        if text.strip().isdigit():
            val = int(text.strip())
            clamped = max(self.min_val, min(self.max_val, val))
            self._value = clamped
            self.valueChanged.emit(clamped)

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
        bg_color = "#27272A" if self.is_dark else "#F4F4F6"
        border_color = "#3F3F46" if self.is_dark else "#E4E4E7"
        text_primary = "#F4F4F5" if self.is_dark else "#18181B"
        text_secondary = "#A1A1AA" if self.is_dark else "#71717A"
        focus_border = "#C2410C" if self.is_dark else "#BA3F1A"

        self.setStyleSheet(f"""
            NumberPill {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 11px;
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
                font-size: 13px;
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
                font-size: 12px;
                font-weight: 500;
                padding-left: 2px;
            }}
        """)


class DurationPillSelector(QWidget):
    """
    Two-pill duration picker for Hours and Minutes with a confirmation check button,
    matching the reference design [ 2 Hr. ] [ 30 Min. ] [ ✓ ].
    Drop-in compatible with QSpinBox API (.value(), .setValue(), .setRange(), .valueChanged).
    """

    valueChanged = pyqtSignal(int)
    confirmed = pyqtSignal(int)

    def __init__(
        self,
        min_minutes: int = 1,
        max_minutes: int = 720,
        default_minutes: int = 5,
        is_dark: bool = True,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.min_minutes = min_minutes
        self.max_minutes = max_minutes
        self.is_dark = is_dark

        self._init_ui()
        self.setValue(default_minutes)

    def _init_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # 1. Hours Pill [ 0 Hr. ]
        self.hr_pill = NumberPill(
            unit="Hr.",
            min_val=0,
            max_val=self.max_minutes // 60,
            default_val=0,
            is_dark=self.is_dark,
            parent=self,
        )
        self.hr_pill.setFixedWidth(82)
        self.hr_pill.valueChanged.connect(self._on_sub_value_changed)
        self.hr_pill.editingFinished.connect(self._on_editing_finished)
        layout.addWidget(self.hr_pill)

        # 2. Minutes Pill [ 30 Min. ]
        self.min_pill = NumberPill(
            unit="Min.",
            min_val=0,
            max_val=59,
            default_val=5,
            is_dark=self.is_dark,
            parent=self,
        )
        self.min_pill.setFixedWidth(92)
        self.min_pill.valueChanged.connect(self._on_sub_value_changed)
        self.min_pill.editingFinished.connect(self._on_editing_finished)
        layout.addWidget(self.min_pill)

        # 3. Check Button [ ✓ ]
        self.check_btn = CheckButton(is_dark=self.is_dark, size=38, parent=self)
        self.check_btn.clicked.connect(self._on_confirm_clicked)
        layout.addWidget(self.check_btn)

    def value(self) -> int:
        total = self.hr_pill.value() * 60 + self.min_pill.value()
        return max(self.min_minutes, min(self.max_minutes, total))

    def setValue(self, total_minutes: int) -> None:
        total = max(self.min_minutes, min(self.max_minutes, int(total_minutes)))
        hrs = total // 60
        mins = total % 60
        self.hr_pill.blockSignals(True)
        self.min_pill.blockSignals(True)
        self.hr_pill.setValue(hrs)
        self.min_pill.setValue(mins)
        self.hr_pill.blockSignals(False)
        self.min_pill.blockSignals(False)
        self.valueChanged.emit(total)

    def setRange(self, min_val: int, max_val: int) -> None:
        self.min_minutes = min_val
        self.max_minutes = max_val
        self.hr_pill.setRange(0, max_val // 60)
        self.setValue(self.value())

    def setSuffix(self, suffix: str) -> None:
        # Compatibility stub for QSpinBox
        pass

    def set_theme(self, is_dark: bool) -> None:
        self.is_dark = is_dark
        self.hr_pill.set_theme(is_dark)
        self.min_pill.set_theme(is_dark)
        self.check_btn.set_theme(is_dark)

    def setStyleSheet(self, qss: str) -> None:
        # Compatibility with apply_theme
        pass

    def _on_sub_value_changed(self, _) -> None:
        self.valueChanged.emit(self.value())

    def _on_editing_finished(self) -> None:
        val = self.value()
        self.setValue(val)

    def _on_confirm_clicked(self) -> None:
        self.clearFocus()
        self.hr_pill.input_edit.clearFocus()
        self.min_pill.input_edit.clearFocus()
        val = self.value()
        self.confirmed.emit(val)
        self.valueChanged.emit(val)


class PillSpinBox(QWidget):
    """
    Single-pill number picker with custom unit suffix and check button,
    matching the reference design [ 5 snapshots ] [ ✓ ].
    Drop-in compatible with QSpinBox API (.value(), .setValue(), .setRange(), .setSuffix()).
    """

    valueChanged = pyqtSignal(int)
    confirmed = pyqtSignal(int)

    def __init__(
        self,
        min_val: int = 1,
        max_val: int = 100,
        default_val: int = 5,
        unit: str = "snapshots",
        is_dark: bool = True,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.is_dark = is_dark
        self.min_val = min_val
        self.max_val = max_val
        self.unit = unit

        self._init_ui(default_val)

    def _init_ui(self, default_val: int) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # 1. Number Pill
        self.pill = NumberPill(
            unit=self.unit,
            min_val=self.min_val,
            max_val=self.max_val,
            default_val=default_val,
            is_dark=self.is_dark,
            parent=self,
        )
        self.pill.setFixedWidth(136)
        self.pill.valueChanged.connect(self._on_value_changed)
        layout.addWidget(self.pill)

        # 2. Check Button [ ✓ ]
        self.check_btn = CheckButton(is_dark=self.is_dark, size=38, parent=self)
        self.check_btn.clicked.connect(self._on_confirm_clicked)
        layout.addWidget(self.check_btn)

    def value(self) -> int:
        return self.pill.value()

    def setValue(self, val: int) -> None:
        self.pill.setValue(val)

    def setRange(self, min_val: int, max_val: int) -> None:
        self.min_val = min_val
        self.max_val = max_val
        self.pill.setRange(min_val, max_val)

    def setSuffix(self, suffix: str) -> None:
        clean = suffix.strip()
        self.unit = clean
        self.pill.set_unit(clean)
        if len(clean) > 8:
            self.pill.setFixedWidth(146)
        elif len(clean) > 5:
            self.pill.setFixedWidth(128)
        else:
            self.pill.setFixedWidth(96)

    def setFixedWidth(self, width: int) -> None:
        self.pill.setFixedWidth(max(70, width - 46))

    def set_theme(self, is_dark: bool) -> None:
        self.is_dark = is_dark
        self.pill.set_theme(is_dark)
        self.check_btn.set_theme(is_dark)

    def setStyleSheet(self, qss: str) -> None:
        # Compatibility with apply_theme
        pass

    def _on_value_changed(self, val: int) -> None:
        self.valueChanged.emit(val)

    def _on_confirm_clicked(self) -> None:
        self.clearFocus()
        self.pill.input_edit.clearFocus()
        val = self.value()
        self.confirmed.emit(val)
        self.valueChanged.emit(val)
