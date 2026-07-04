from PySide6 import QtCore, QtGui, QtWidgets

PALETTE = {
    "bg": "#07111F",
    "bg_alt": "#0B1728",
    "panel": "#0F1C2E",
    "panel_alt": "#132238",
    "panel_soft": "#18293F",
    "border": "#223349",
    "text": "#F8FAFC",
    "muted": "#94A3B8",
    "subtle": "#64748B",
    "accent": "#F97316",
    "blue": "#38BDF8",
    "green": "#22C55E",
    "orange": "#FB923C",
    "red": "#F43F5E",
}

APP_FONT_FAMILY = "Lexend"
FIELD_HEIGHT = 48
SMALL_FIELD_HEIGHT = 42


def _color(hex_color, alpha=255):
    color = QtGui.QColor(hex_color)
    color.setAlpha(alpha)
    return color


def polish(widget):
    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)
    widget.update()


def normalize_ui_text(text):
    if isinstance(text, str) and "Ã" in text:
        try:
            return text.encode("latin1").decode("utf-8")
        except UnicodeError:
            return text
    return text


def apply_shadow(widget, blur=36, y_offset=14, color="#020817", alpha=110):
    shadow = QtWidgets.QGraphicsDropShadowEffect(widget)
    shadow.setBlurRadius(blur)
    shadow.setOffset(0, y_offset)
    shadow.setColor(_color(color, alpha))
    widget.setGraphicsEffect(shadow)
    return shadow


def make_panel(master, kind="surface"):
    frame = QtWidgets.QFrame(master)
    frame.setProperty("card", True)
    frame.setProperty("kind", kind)
    return frame


def make_badge(master, text, tone="accent"):
    frame = QtWidgets.QFrame(master)
    frame.setProperty("badge", tone)
    layout = QtWidgets.QHBoxLayout(frame)
    layout.setContentsMargins(10, 4, 10, 4)
    layout.setSpacing(0)
    label = QtWidgets.QLabel(normalize_ui_text(text), frame)
    label.setProperty("badgeTone", tone)
    label.setAlignment(QtCore.Qt.AlignCenter)
    layout.addWidget(label)
    return frame


def style_button(button, accent=False, quiet=False, nav=False):
    button.setProperty("accent", accent)
    button.setProperty("quiet", quiet)
    button.setProperty("nav", nav)
    polish(button)


class ComboFieldDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, parent=None, center=True):
        super().__init__(parent)
        self.center = center

    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        option.displayAlignment = (
            QtCore.Qt.AlignCenter if self.center else QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter
        )


class CenteredComboBox(QtWidgets.QComboBox):
    def __init__(self, parent=None, center=True):
        super().__init__(parent)
        self._center_text = center

    def setCenterText(self, center):
        self._center_text = center
        self.update()

    def _fit_text_font(self, text, available_width):
        font = QtGui.QFont(self.font())
        min_size = float(self.property("minimumTextPointSize") or 8)
        point_size = font.pointSizeF()
        if point_size <= 0:
            point_size = 10.0
            font.setPointSizeF(point_size)

        while point_size > min_size and QtGui.QFontMetrics(font).horizontalAdvance(text) > available_width:
            point_size -= 0.5
            font.setPointSizeF(point_size)
        return font

    def paintEvent(self, _event):
        painter = QtWidgets.QStylePainter(self)
        painter.setPen(self.palette().color(QtGui.QPalette.Text))

        option = QtWidgets.QStyleOptionComboBox()
        self.initStyleOption(option)
        option.currentText = ""
        painter.drawComplexControl(QtWidgets.QStyle.CC_ComboBox, option)

        if self._center_text:
            text_rect = self.rect()
            alignment = QtCore.Qt.AlignCenter
        else:
            text_rect = self.style().subControlRect(
                QtWidgets.QStyle.CC_ComboBox,
                option,
                QtWidgets.QStyle.SC_ComboBoxEditField,
                self,
            )
            alignment = QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter
        draw_rect = text_rect.adjusted(8, 0, -8, 0)
        text = self.currentText()
        painter.setFont(self._fit_text_font(text, draw_rect.width()))
        painter.drawText(draw_rect, alignment, text)


class ClickableDateEdit(QtWidgets.QDateEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._calendar_popup = None
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setKeyboardTracking(False)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.setFocus(QtCore.Qt.MouseFocusReason)
            self._sync_display_text()
            self.open_calendar_popup()
            event.accept()
            return
        super().mousePressEvent(event)

    def keyPressEvent(self, event):
        if event.key() in (QtCore.Qt.Key_Space, QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
            self.open_calendar_popup()
            return
        super().keyPressEvent(event)

    def open_calendar_popup(self):
        if self._calendar_popup and self._calendar_popup.isVisible():
            self._calendar_popup.close()
            return

        if not self.date().isValid():
            self.setDate(QtCore.QDate.currentDate())
        self._sync_display_text()

        app = QtWidgets.QApplication.instance()
        if app:
            for widget in app.topLevelWidgets():
                if widget is not self._calendar_popup and widget.objectName() == "datePickerPopup":
                    widget.close()

        popup = QtWidgets.QFrame(None, QtCore.Qt.Popup)
        popup.setObjectName("datePickerPopup")
        popup.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        popup.setStyleSheet(
            "QFrame#datePickerPopup {"
            "background: rgba(11, 23, 40, 246);"
            "border: 1px solid rgba(255, 255, 255, 28);"
            "border-radius: 18px;"
            "}"
        )
        layout = QtWidgets.QVBoxLayout(popup)
        layout.setContentsMargins(8, 8, 8, 8)
        calendar = QtWidgets.QCalendarWidget(popup)
        calendar.setSelectedDate(self.date())
        calendar.clicked.connect(lambda date: self._select_popup_date(date, popup))
        layout.addWidget(calendar)
        popup.resize(330, 270)
        popup.move(self.mapToGlobal(QtCore.QPoint(0, self.height() + 6)))
        popup.destroyed.connect(lambda *_: setattr(self, "_calendar_popup", None))
        self._calendar_popup = popup
        popup.show()

    def _select_popup_date(self, date, popup):
        self.setDate(date)
        self._sync_display_text()
        popup.close()

    def _sync_display_text(self):
        line_edit = self.lineEdit()
        if line_edit:
            line_edit.setAlignment(QtCore.Qt.AlignCenter)
            line_edit.setText(self.date().toString(self.displayFormat()))


def style_text_field(field, center=False, width=None, height=FIELD_HEIGHT):
    if width is not None:
        field.setFixedWidth(width)
    field.setProperty("formField", height > FIELD_HEIGHT)
    field.setProperty("compactFormField", height < FIELD_HEIGHT)
    field.setAlignment(
        QtCore.Qt.AlignCenter if center else QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter
    )
    polish(field)
    field.setFixedHeight(height)


def style_combo_field(combo, center=True, height=FIELD_HEIGHT):
    combo.setInsertPolicy(QtWidgets.QComboBox.NoInsert)
    combo.setProperty("formField", height > FIELD_HEIGHT)
    combo.setProperty("compactFormField", height < FIELD_HEIGHT)
    if isinstance(combo, CenteredComboBox):
        combo.setEditable(False)
        combo.setCenterText(center)
    else:
        combo.setEditable(False)
    combo.setFocusPolicy(QtCore.Qt.StrongFocus)
    combo.setCursor(QtCore.Qt.PointingHandCursor)
    combo.setMaxVisibleItems(12)
    combo.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContentsOnFirstShow)
    polish(combo)
    combo.setFixedHeight(height)


def style_date_field(date_edit, width=220, height=FIELD_HEIGHT, display_format="dd-MM-yyyy"):
    date_edit.setCalendarPopup(not isinstance(date_edit, ClickableDateEdit))
    date_edit.setDisplayFormat(display_format)
    date_edit.setAlignment(QtCore.Qt.AlignCenter)
    date_edit.setKeyboardTracking(False)
    if isinstance(date_edit, ClickableDateEdit):
        date_edit.setReadOnly(True)
        date_edit.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
    else:
        date_edit.setButtonSymbols(QtWidgets.QAbstractSpinBox.UpDownArrows)
    if date_edit.lineEdit():
        date_edit.lineEdit().setAlignment(QtCore.Qt.AlignCenter)
    if width is not None:
        date_edit.setFixedWidth(width)
    date_edit.setProperty("formField", height > FIELD_HEIGHT)
    date_edit.setProperty("compactFormField", height < FIELD_HEIGHT)
    date_edit.setProperty("dateField", True)
    polish(date_edit)
    date_edit.setFixedHeight(height)
    if isinstance(date_edit, ClickableDateEdit):
        date_edit._sync_display_text()


def animate_widget_entry(widget, duration=240, y_offset=18):
    if widget.isWindow():
        end_pos = widget.pos()
        start_pos = end_pos + QtCore.QPoint(0, y_offset)
        widget.move(start_pos)
        widget.setWindowOpacity(0.0)

        position_anim = QtCore.QPropertyAnimation(widget, b"pos", widget)
        position_anim.setDuration(duration)
        position_anim.setStartValue(start_pos)
        position_anim.setEndValue(end_pos)
        position_anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)

        opacity_anim = QtCore.QPropertyAnimation(widget, b"windowOpacity", widget)
        opacity_anim.setDuration(duration)
        opacity_anim.setStartValue(0.0)
        opacity_anim.setEndValue(1.0)
        opacity_anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)

        group = QtCore.QParallelAnimationGroup(widget)
        group.addAnimation(position_anim)
        group.addAnimation(opacity_anim)
        widget._entry_animation = group
        group.start(QtCore.QAbstractAnimation.DeleteWhenStopped)
        return group

    effect = widget.graphicsEffect()
    if not isinstance(effect, QtWidgets.QGraphicsOpacityEffect):
        effect = QtWidgets.QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)

    effect.setOpacity(0.0)
    animation = QtCore.QPropertyAnimation(effect, b"opacity", widget)
    animation.setDuration(duration)
    animation.setStartValue(0.0)
    animation.setEndValue(1.0)
    animation.setEasingCurve(QtCore.QEasingCurve.OutCubic)
    widget._entry_animation = animation
    animation.start(QtCore.QAbstractAnimation.DeleteWhenStopped)
    return animation


def make_label(master, text, **kw):
    label = QtWidgets.QLabel(normalize_ui_text(text), master)
    align = kw.get("anchor")
    if align == "w":
        label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
    elif align == "center":
        label.setAlignment(QtCore.Qt.AlignCenter)

    if kw.get("muted"):
        label.setProperty("muted", True)
    if kw.get("eyebrow"):
        label.setProperty("eyebrow", True)
    if kw.get("hero"):
        label.setProperty("hero", True)

    font = kw.get("font")
    if font:
        family = font[0] if len(font) > 0 else None
        size = font[1] if len(font) > 1 else None
        weight = QtGui.QFont.Bold if len(font) > 2 and "bold" in str(font[2]).lower() else QtGui.QFont.Normal
        qfont = label.font()
        qfont.setFamily(APP_FONT_FAMILY if family else APP_FONT_FAMILY)
        if size:
            qfont.setPointSize(int(size))
        qfont.setWeight(weight)
        label.setFont(qfont)
    return label


def install_messagebox_tweaks():
    if getattr(QtWidgets.QMessageBox, "_estoque_tweaked", False):
        return

    messagebox_style = (
        "QMessageBox {"
        "background: #0B1728;"
        "color: #F8FAFC;"
        "}"
        "QMessageBox QLabel {"
        "color: #F8FAFC;"
        "font-size: 13px;"
        "font-weight: 600;"
        "background: transparent;"
        "}"
        "QMessageBox QPushButton {"
        "background: rgba(255, 255, 255, 0.08);"
        "color: #F8FAFC;"
        "border: 1px solid rgba(255, 255, 255, 28);"
        "border-radius: 12px;"
        "padding: 8px 16px;"
        "min-width: 82px;"
        "font-weight: 700;"
        "}"
        "QMessageBox QPushButton:hover {"
        "background: rgba(255, 255, 255, 0.14);"
        "}"
        "QMessageBox QPushButton:pressed {"
        "background: rgba(14, 165, 233, 0.28);"
        "border: 1px solid rgba(125, 211, 252, 0.72);"
        "}"
    )

    def show_message(parent, title, text, icon, buttons, defaultButton):
        msg = QtWidgets.QMessageBox(parent)
        msg.setWindowTitle(title)
        msg.setText(text)
        msg.setTextFormat(QtCore.Qt.PlainText)
        msg.setStyleSheet(messagebox_style)
        msg.setStandardButtons(buttons)
        if defaultButton != QtWidgets.QMessageBox.NoButton:
            msg.setDefaultButton(defaultButton)
        msg.setIcon(icon)
        return msg.exec()

    def information(parent, title, text, buttons=QtWidgets.QMessageBox.Ok, defaultButton=QtWidgets.QMessageBox.NoButton):
        return show_message(parent, title, text, QtWidgets.QMessageBox.Information, buttons, defaultButton)

    def warning(parent, title, text, buttons=QtWidgets.QMessageBox.Ok, defaultButton=QtWidgets.QMessageBox.NoButton):
        return show_message(parent, title, text, QtWidgets.QMessageBox.Warning, buttons, defaultButton)

    def critical(parent, title, text, buttons=QtWidgets.QMessageBox.Ok, defaultButton=QtWidgets.QMessageBox.NoButton):
        return show_message(parent, title, text, QtWidgets.QMessageBox.Critical, buttons, defaultButton)

    def question(
        parent,
        title,
        text,
        buttons=QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
        defaultButton=QtWidgets.QMessageBox.NoButton,
    ):
        return show_message(parent, title, text, QtWidgets.QMessageBox.Question, buttons, defaultButton)

    QtWidgets.QMessageBox.information = staticmethod(information)
    QtWidgets.QMessageBox.warning = staticmethod(warning)
    QtWidgets.QMessageBox.critical = staticmethod(critical)
    QtWidgets.QMessageBox.question = staticmethod(question)
    QtWidgets.QMessageBox._estoque_tweaked = True


def pad_values(valores, largura=22):
    return [v.ljust(largura) for v in valores]


class GradientCanvas(QtWidgets.QWidget):
    def paintEvent(self, _event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        gradient = QtGui.QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, _color(PALETTE["bg"]))
        gradient.setColorAt(1, _color(PALETTE["bg_alt"]))
        painter.fillRect(self.rect(), gradient)

        blobs = (
            (-60, -30, 320, PALETTE["accent"], 42),
            (self.width() - 260, -70, 360, PALETTE["green"], 28),
            (self.width() - 220, self.height() - 220, 300, PALETTE["blue"], 22),
        )
        for x, y, size, color, alpha in blobs:
            radial = QtGui.QRadialGradient(x + size / 2, y + size / 2, size / 2)
            radial.setColorAt(0, _color(color, alpha))
            radial.setColorAt(1, _color(color, 0))
            painter.setBrush(radial)
            painter.setPen(QtCore.Qt.NoPen)
            painter.drawEllipse(QtCore.QRectF(x, y, size, size))

        pen = QtGui.QPen(_color("#FFFFFF", 10))
        pen.setWidth(1)
        painter.setPen(pen)
        top = 110
        step = 72
        for y in range(top, self.height(), step):
            painter.drawLine(32, y, self.width() - 32, y)


class MetricCard(QtWidgets.QFrame):
    TONES = {
        "blue": ("#38BDF8", "#D9F3FF"),
        "accent": ("#F97316", "#FFE5CF"),
        "green": ("#22C55E", "#DCFCE7"),
    }

    def __init__(self, parent, title, tone="blue"):
        super().__init__(parent)
        self.tone = tone if tone in self.TONES else "blue"
        self._ratio = 0.58
        self.setProperty("card", True)
        self.setProperty("kind", "metric")
        apply_shadow(self, blur=28, y_offset=10, alpha=60)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(8)
        layout.setAlignment(QtCore.Qt.AlignCenter)

        self.title_label = QtWidgets.QLabel(title, self)
        self.title_label.setProperty("muted", True)
        self.title_label.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(self.title_label, 0, QtCore.Qt.AlignCenter)

        self.value_label = QtWidgets.QLabel("0", self)
        self.value_label.setProperty("metricValue", True)
        self.value_label.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(self.value_label, 0, QtCore.Qt.AlignCenter)

        self.detail_label = QtWidgets.QLabel("", self)
        self.detail_label.setProperty("metricDetail", True)
        self.detail_label.setAlignment(QtCore.Qt.AlignCenter)
        self.detail_label.setWordWrap(True)
        layout.addWidget(self.detail_label, 0, QtCore.Qt.AlignCenter)

        self._apply_tone()

    def _apply_tone(self):
        tone_color, text_color = self.TONES[self.tone]
        self.detail_label.setStyleSheet(
            f"color: {tone_color}; font-size: 11px; font-weight: 700;"
        )
        self.value_label.setStyleSheet(f"color: {text_color}; font-size: 30px; font-weight: 700;")

    def resizeEvent(self, event):
        super().resizeEvent(event)

    def set_data(self, value, detail, ratio=0.58):
        self.value_label.setText(str(value))
        self.detail_label.setText(detail)
        self._ratio = max(0.16, min(1.0, ratio))


class PillDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, palette_map, parent=None):
        super().__init__(parent)
        self.palette_map = {key.lower(): value for key, value in palette_map.items()}

    def paint(self, painter, option, index):
        opt = QtWidgets.QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        opt.text = ""
        if opt.widget:
            opt.widget.style().drawControl(QtWidgets.QStyle.CE_ItemViewItem, opt, painter, opt.widget)

        text = str(index.data() or "").strip()
        if not text:
            return

        bg, fg = self.palette_map.get(text.lower(), ("#132238", "#D9E2F2"))
        rect = option.rect.adjusted(10, 8, -10, -8)

        painter.save()
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(_color(bg))
        painter.drawRoundedRect(rect, 12, 12)

        font = option.font
        font.setPointSize(max(9, font.pointSize() - 1))
        font.setWeight(QtGui.QFont.DemiBold)
        painter.setFont(font)
        painter.setPen(_color(fg))
        painter.drawText(rect, QtCore.Qt.AlignCenter, text)
        painter.restore()


class Toast:
    """Show transient feedback using a window-owned Qt status bar."""
    def __init__(self, parent, text, timeout_ms=4200):
        window = parent
        if isinstance(parent, QtWidgets.QApplication):
            window = parent.activeWindow()
        elif isinstance(parent, QtWidgets.QWidget):
            window = parent.window()

        if not isinstance(window, QtWidgets.QMainWindow):
            return

        status_bar = window.statusBar()
        status_bar.setSizeGripEnabled(False)
        status_bar.setStyleSheet(
            f"QStatusBar {{ background: {PALETTE['panel_alt']}; color: {PALETTE['text']}; "
            f"border-top: 1px solid {PALETTE['border']}; padding: 4px 10px; }}"
        )
        status_bar.showMessage(str(text), timeout_ms)
