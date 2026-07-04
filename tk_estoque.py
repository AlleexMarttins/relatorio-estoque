import os
import sys
from PySide6 import QtCore, QtGui, QtWidgets
import utils_estoque as utils
from system.filters_section import FiltersMixin
from system.table_section import TableMixin
from system.forms_section import FormsMixin
from system.suppliers_section import SuppliersMixin
from system.conferentes_section import ConferentesMixin
from system.settings_section import SettingsMixin
from system.actions_stack import ActionsMixin
from system.ui_components import (
    GradientCanvas,
    APP_FONT_FAMILY,
    PALETTE,
    apply_shadow,
    install_messagebox_tweaks,
    make_panel,
    style_text_field,
)

class EstoqueApp(
    QtWidgets.QMainWindow,
    FiltersMixin,
    TableMixin,
    FormsMixin,
    SuppliersMixin,
    ConferentesMixin,
    SettingsMixin,
    ActionsMixin,
):
    def __init__(self):
        super().__init__()
        utils.install_global_exception_hook()
        utils.diagnostic_log("app_init_start", argv=sys.argv)
        self._install_app_font()
        install_messagebox_tweaks()
        self.root = self
        self.setWindowTitle("Relatorio do Estoque")
        self.resize(1450, 800)
        icon_path = utils.resource_path("icone.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QtGui.QIcon(icon_path))

        self._build_layout()
        self._apply_style()
        self.setMinimumSize(1280, 760)

        self.settings = utils.load_settings()
        self.mac = utils.get_mac_address()
        self.user = utils.get_or_create_user(utils.supabase, self.mac)

        self._build_filters()
        self._build_table()
        self._build_actions_stack()

        if not self.user:
            QtCore.QTimer.singleShot(200, self._ask_name_non_modal)

        QtCore.QTimer.singleShot(60, self.refresh_table)
        QtCore.QTimer.singleShot(120, self.update_recent_list)
        QtCore.QTimer.singleShot(120, self.warning_month_filter)

        self._escape_shortcut = QtGui.QShortcut(
            QtGui.QKeySequence(QtCore.Qt.Key_Escape),
            self,
        )
        self._escape_shortcut.activated.connect(self._handle_escape)
        self._setup_tooltip_support()
        self._bind_search_suggestions()
        utils.poll_notifications(self)
        utils.diagnostic_log("app_init_done")

    def _install_app_font(self):
        app = QtWidgets.QApplication.instance()
        if not app:
            return
        app.setApplicationName("Relatorio do Estoque")
        if hasattr(app, "setApplicationDisplayName"):
            app.setApplicationDisplayName("Relatorio do Estoque")

        font_path = utils.resource_path(os.path.join("assets", "fonts", "Lexend.ttf"))
        if os.path.exists(font_path):
            font_id = QtGui.QFontDatabase.addApplicationFont(font_path)
            families = QtGui.QFontDatabase.applicationFontFamilies(font_id) if font_id >= 0 else []
            if families:
                app.setFont(QtGui.QFont(families[0]))
                return

        app.setFont(QtGui.QFont(APP_FONT_FAMILY))

    def _build_layout(self):
        central = GradientCanvas(self)
        central.setObjectName("appRoot")
        self.setCentralWidget(central)
        root_layout = QtWidgets.QHBoxLayout(central)
        root_layout.setContentsMargins(24, 24, 24, 24)
        root_layout.setSpacing(18)

        self.left_container = make_panel(central, "sidebar")
        self.left_container.setObjectName("sidebarPanel")
        self.left_container.setFixedWidth(252)
        left_container_layout = QtWidgets.QVBoxLayout(self.left_container)
        left_container_layout.setContentsMargins(0, 0, 0, 0)
        left_container_layout.setSpacing(0)

        self.left_scroll = QtWidgets.QScrollArea(self.left_container)
        self.left_scroll.setObjectName("sidebarScroll")
        self.left_scroll.setWidgetResizable(True)
        self.left_scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.left_scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.left_frame = QtWidgets.QFrame()
        self.left_frame.setObjectName("leftFrame")
        self.left_layout = QtWidgets.QVBoxLayout(self.left_frame)
        self.left_layout.setContentsMargins(12, 12, 12, 12)
        self.left_layout.setSpacing(10)
        self.left_scroll.setWidget(self.left_frame)
        left_container_layout.addWidget(self.left_scroll)
        root_layout.addWidget(self.left_container)
        apply_shadow(self.left_container, blur=38, y_offset=18, alpha=70)

        self.main_frame = QtWidgets.QFrame(central)
        self.main_frame.setObjectName("mainWorkspace")
        self.main_layout = QtWidgets.QVBoxLayout(self.main_frame)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(16)

        self.hero_frame = make_panel(self.main_frame, "heroTitle")
        self.hero_frame.setObjectName("heroTitleCard")
        self.hero_layout = QtWidgets.QVBoxLayout(self.hero_frame)
        self.hero_layout.setContentsMargins(28, 22, 28, 22)
        self.hero_layout.setSpacing(8)
        self.main_layout.addWidget(self.hero_frame)
        apply_shadow(self.hero_frame, blur=40, y_offset=16, alpha=58)

        self.search_frame = make_panel(self.main_frame, "toolbar")
        self.search_frame.setObjectName("toolbarCard")
        self.search_layout = QtWidgets.QHBoxLayout(self.search_frame)
        self.search_layout.setContentsMargins(18, 16, 18, 16)
        self.search_layout.setSpacing(14)
        self.main_layout.addWidget(self.search_frame)
        root_layout.addWidget(self.main_frame, 1)
        apply_shadow(self.search_frame, blur=34, y_offset=14, alpha=52)

        self.actions_frame = make_panel(central, "actionRail")
        self.actions_frame.setObjectName("actionRail")
        self.actions_frame.setFixedWidth(412)
        actions_frame_layout = QtWidgets.QVBoxLayout(self.actions_frame)
        actions_frame_layout.setContentsMargins(0, 0, 0, 0)
        actions_frame_layout.setSpacing(0)
        self.actions_scroll = QtWidgets.QScrollArea(self.actions_frame)
        self.actions_scroll.setObjectName("actionRailScroll")
        self.actions_scroll.setWidgetResizable(True)
        self.actions_scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.actions_scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.actions_body = QtWidgets.QFrame()
        self.actions_body.setObjectName("actionsBody")
        self.actions_layout = QtWidgets.QVBoxLayout(self.actions_body)
        self.actions_layout.setContentsMargins(16, 16, 28, 16)
        self.actions_layout.setSpacing(14)
        self.actions_scroll.setWidget(self.actions_body)
        actions_frame_layout.addWidget(self.actions_scroll)
        root_layout.addWidget(self.actions_frame)
        apply_shadow(self.actions_frame, blur=38, y_offset=18, alpha=70)

    def _apply_style(self):
        action_orange = "#D97706"
        action_orange_hover = "#E08A1E"
        action_pressed = "#0EA5E9"
        self.setStyleSheet(
            "QMainWindow { background: #07111F; color: #F8FAFC; }"
            f"QWidget {{ font-family: '{APP_FONT_FAMILY}'; }}"
            f"QWidget#appRoot {{ background: transparent; color: #F8FAFC; font-family: '{APP_FONT_FAMILY}'; font-size: 12px; }}"
            "QFrame { background: transparent; color: #F8FAFC; }"
            "QFrame[card=\"true\"] {"
            "background: rgba(45, 55, 72, 214);"
            "border: 1px solid rgba(255, 255, 255, 18);"
            "border-radius: 24px;"
            "}"
            "QFrame[card=\"true\"][kind=\"metric\"] {"
            "background: rgba(39, 48, 63, 224);"
            "border-radius: 22px;"
            "}"
            "QFrame[card=\"true\"][kind=\"heroTitle\"] {"
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:1,"
            "stop:0 rgba(249, 115, 22, 28),"
            "stop:0.45 rgba(36, 45, 59, 238),"
            "stop:1 rgba(56, 189, 248, 24));"
            "border: 1px solid rgba(255, 255, 255, 30);"
            "border-radius: 28px;"
            "}"
            "QFrame[card=\"true\"][kind=\"scopeHighlight\"] {"
            "background: rgba(249, 115, 22, 0.12);"
            "border: 1px solid rgba(251, 146, 60, 0.42);"
            "border-radius: 18px;"
            "}"
            "QFrame#sidebarPanel, QFrame#actionRail {"
            "background: rgba(11, 23, 40, 236);"
            "border: 1px solid rgba(255, 255, 255, 22);"
            "border-radius: 28px;"
            "}"
            "QFrame#toolbarCard {"
            "background: rgba(11, 23, 40, 232);"
            "border: 1px solid rgba(255, 255, 255, 22);"
            "border-radius: 26px;"
            "}"
            "QFrame#leftFrame { background: transparent; border: none; }"
            "QScrollArea#sidebarScroll { background: transparent; border: none; }"
            "QScrollArea#sidebarScroll > QWidget > QWidget { background: transparent; }"
            "QScrollArea#actionRailScroll { background: transparent; border: none; }"
            "QScrollArea#actionRailScroll > QWidget > QWidget { background: transparent; }"
            "QFrame#actionsBody { background: transparent; border: none; }"
            "QLabel { color: #F8FAFC; background: transparent; }"
            "QLabel[muted=\"true\"] { color: #94A3B8; }"
            "QLabel[eyebrow=\"true\"] { color: #94A3B8; font-size: 10px; font-weight: 700; letter-spacing: 1px; }"
            "QLabel[hero=\"true\"] { color: #F8FAFC; font-size: 24px; font-weight: 700; }"
            "QLabel[metricValue=\"true\"] { color: #F8FAFC; font-size: 30px; font-weight: 700; }"
            "QLabel[appTitle=\"true\"] { color: #FFF7ED; font-size: 30px; font-weight: 800; letter-spacing: 0.3px; }"
            "QLabel[appLead=\"true\"] { color: #CBD5E1; font-size: 13px; font-weight: 500; }"
            "QLabel[scopeHeadline=\"true\"] { color: #FFF7ED; font-size: 13px; font-weight: 700; }"
            "QLabel[scopeSupport=\"true\"] { color: #FED7AA; font-size: 11px; font-weight: 600; }"
            "QLabel[filterHeader=\"true\"] {"
            "color: #F8FAFC;"
            "font-size: 15px;"
            "font-weight: 800;"
            "letter-spacing: 0.4px;"
            "}"
            "QLabel[filterSectionLabel=\"true\"] {"
            "color: #FFF7ED;"
            "font-size: 12px;"
            "font-weight: 900;"
            "letter-spacing: 0.2px;"
            "padding: 4px 0px 2px 0px;"
            "}"
            "QLabel[filterFieldLabel=\"true\"] {"
            "color: #B6C2D2;"
            "font-size: 13px;"
            "font-weight: 800;"
            "}"
            "QLabel[filterComboLabel=\"true\"] {"
            "color: #B6C2D2;"
            "font-size: 12px;"
            "font-weight: 800;"
            "letter-spacing: 0.15px;"
            "padding-left: 4px;"
            "}"
            "QFrame[summaryStat=\"true\"] {"
            "background: rgba(8, 18, 32, 150);"
            "border: 1px solid rgba(125, 211, 252, 0.16);"
            "border-radius: 18px;"
            "}"
            "QLabel[summaryLabel=\"true\"] {"
            "color: #94A3B8;"
            "font-size: 10px;"
            "font-weight: 800;"
            "letter-spacing: 0.8px;"
            "}"
            "QLabel[summaryValue=\"true\"] {"
            "color: #F8FAFC;"
            "font-size: 16px;"
            "font-weight: 800;"
            "}"
            "QLineEdit, QComboBox, QTextEdit, QDateEdit, QTableWidget {"
            "background: rgba(8, 18, 32, 208);"
            "color: #F8FAFC;"
            "border: 1px solid rgba(255, 255, 255, 20);"
            "border-radius: 18px;"
            "padding: 10px 12px;"
            "min-height: 24px;"
            "selection-background-color: rgba(56, 189, 248, 70);"
            "}"
            "QLineEdit[formField=\"true\"], QComboBox[formField=\"true\"], QDateEdit[formField=\"true\"] {"
            "min-height: 34px;"
            "padding: 11px 14px;"
            "border-radius: 20px;"
            "}"
            "QLineEdit[compactFormField=\"true\"], QComboBox[compactFormField=\"true\"], QDateEdit[compactFormField=\"true\"] {"
            "min-height: 30px;"
            "padding: 7px 11px;"
            "border-radius: 16px;"
            "}"
            "QTextEdit { padding-top: 12px; }"
            "QLineEdit:focus, QComboBox:focus, QTextEdit:focus, QDateEdit:focus {"
            f"border: 1px solid {PALETTE['blue']};"
            "}"
            "QComboBox::drop-down { border: none; width: 22px; }"
            "QComboBox::down-arrow { image: none; width: 8px; height: 8px; }"
            "QComboBox[supplierField=\"true\"] { font-size: 10px; }"
            "QComboBox[compactFormField=\"true\"]::drop-down { border: none; width: 16px; }"
            "QComboBox[compactFormField=\"true\"]::down-arrow { image: none; width: 7px; height: 7px; }"
            "QComboBox QLineEdit {"
            "background: transparent;"
            "border: none;"
            "padding: 0px;"
            "color: #F8FAFC;"
            "selection-background-color: rgba(56, 189, 248, 70);"
            "}"
            "QComboBox QAbstractItemView {"
            "background: rgba(8, 18, 32, 244);"
            "color: #F8FAFC;"
            "border: 1px solid rgba(255, 255, 255, 20);"
            "border-radius: 16px;"
            "padding: 6px;"
            "selection-background-color: rgba(56, 189, 248, 70);"
            "selection-color: #F8FAFC;"
            "outline: 0;"
            "}"
            "QComboBox QAbstractItemView::item {"
            "min-height: 34px;"
            "padding: 6px 10px;"
            "}"
            "QDateEdit[dateField=\"true\"] {"
            "font-weight: 600;"
            "padding-right: 28px;"
            "border-radius: 16px;"
            "}"
            "QDateEdit[filterDateField=\"true\"] {"
            "font-size: 13px;"
            "font-weight: 700;"
            "padding: 8px 10px;"
            "padding-right: 10px;"
            "}"
            "QDateEdit[dateField=\"true\"]::drop-down {"
            "subcontrol-origin: padding;"
            "subcontrol-position: top right;"
            "width: 28px;"
            "border: none;"
            "}"
            "QDateEdit[dateField=\"true\"]::down-arrow {"
            "width: 8px;"
            "height: 8px;"
            "}"
            "QDateEdit[dateField=\"true\"][compactFormField=\"true\"] {"
            "padding-right: 14px;"
            "}"
            "QDateEdit[dateField=\"true\"][compactFormField=\"true\"]::drop-down {"
            "width: 12px;"
            "border-left: 1px solid rgba(56, 189, 248, 0.18);"
            "background: rgba(56, 189, 248, 0.10);"
            "}"
            "QDateEdit[dateField=\"true\"][compactFormField=\"true\"]::up-button, "
            "QDateEdit[dateField=\"true\"][compactFormField=\"true\"]::down-button {"
            "width: 12px;"
            "border-left: 1px solid rgba(56, 189, 248, 0.18);"
            "background: rgba(56, 189, 248, 0.10);"
            "}"
            "QDateEdit[dateField=\"true\"][compactFormField=\"true\"]::down-arrow {"
            "width: 6px;"
            "height: 6px;"
            "}"
            "QCalendarWidget QWidget {"
            "background: rgba(11, 23, 40, 246);"
            "color: #F8FAFC;"
            "}"
            "QCalendarWidget QToolButton {"
            "background: rgba(255, 255, 255, 0.06);"
            "color: #F8FAFC;"
            "border: 1px solid rgba(255, 255, 255, 12);"
            "border-radius: 12px;"
            "padding: 6px 10px;"
            "}"
            "QCalendarWidget QSpinBox {"
            "background: rgba(8, 18, 32, 208);"
            "color: #F8FAFC;"
            "border: 1px solid rgba(255, 255, 255, 16);"
            "border-radius: 12px;"
            "padding: 4px 8px;"
            "}"
            "QCalendarWidget QAbstractItemView {"
            "selection-background-color: rgba(56, 189, 248, 0.32);"
            "selection-color: #F8FAFC;"
            "background: rgba(11, 23, 40, 246);"
            "border: none;"
            "outline: 0;"
            "}"
            "QPushButton {"
            "background: rgba(255, 255, 255, 0.08);"
            "color: #E2E8F0;"
            "border: 1px solid rgba(255, 255, 255, 14);"
            "border-radius: 16px;"
            "padding: 10px 14px;"
            "font-weight: 600;"
            "}"
            "QPushButton:hover { background: rgba(255, 255, 255, 0.14); }"
            "QPushButton:pressed, QPushButton[pressedFeedback=\"true\"] {"
            "background: rgba(14, 165, 233, 0.28);"
            "border: 1px solid rgba(125, 211, 252, 0.72);"
            "color: #F8FAFC;"
            "}"
            "QPushButton[accent=\"true\"] {"
            f"background: {action_orange};"
            "color: #FFF7ED;"
            "border: none;"
            "font-weight: 700;"
            "}"
            f"QPushButton[accent=\"true\"]:hover {{ background: {action_orange_hover}; }}"
            "QPushButton[accent=\"true\"]:pressed, QPushButton[accent=\"true\"][pressedFeedback=\"true\"] {"
            f"background: {action_pressed};"
            "color: #F8FAFC;"
            "border: none;"
            "}"
            "QPushButton[quiet=\"true\"] {"
            "background: rgba(11, 23, 40, 0.72);"
            "color: #D7E0EE;"
            "border: 1px solid rgba(255, 255, 255, 16);"
            "}"
            "QPushButton[quiet=\"true\"]:hover { background: rgba(255, 255, 255, 0.10); }"
            "QPushButton[quiet=\"true\"]:pressed, QPushButton[quiet=\"true\"][pressedFeedback=\"true\"] {"
            "background: rgba(14, 165, 233, 0.18);"
            "border: 1px solid rgba(125, 211, 252, 0.56);"
            "color: #F8FAFC;"
            "}"
            "QPushButton[nav=\"true\"] {"
            "text-align: left;"
            "padding: 12px 14px;"
            "font-size: 12px;"
            "}"
            "QPushButton[filterToggleButton=\"true\"] {"
            "font-family: 'Segoe UI';"
            "font-size: 12px;"
            "font-weight: 700;"
            "letter-spacing: 0.2px;"
            "}"
            "QToolButton {"
            "background: rgba(11, 23, 40, 0.72);"
            "border: 1px solid rgba(255, 255, 255, 16);"
            "border-radius: 16px;"
            "padding: 10px;"
            "}"
            "QToolButton:hover { background: rgba(255, 255, 255, 0.10); }"
            "QToolButton[filterToggleButton=\"true\"] {"
            "background: rgba(255, 255, 255, 0.08);"
            "color: #E2E8F0;"
            "border: 1px solid rgba(255, 255, 255, 14);"
            "border-radius: 16px;"
            "padding: 11px 14px;"
            "font-family: 'Segoe UI';"
            "font-size: 12px;"
            "font-weight: 700;"
            "text-align: left;"
            "}"
            "QToolButton[filterToggleButton=\"true\"]:hover {"
            "background: rgba(255, 255, 255, 0.14);"
            "}"
            "QToolButton[filterToggleButton=\"true\"]:pressed, "
            "QToolButton[filterToggleButton=\"true\"][pressedFeedback=\"true\"] {"
            "background: rgba(14, 165, 233, 0.28);"
            "border: 1px solid rgba(125, 211, 252, 0.72);"
            "color: #F8FAFC;"
            "}"
            "QToolButton#searchIconButton {"
            "background: rgba(217, 119, 6, 0.18);"
            "border: 1px solid rgba(245, 158, 11, 0.58);"
            "border-radius: 18px;"
            "padding: 8px;"
            "}"
            "QToolButton#searchIconButton:hover { background: rgba(217, 119, 6, 0.26); }"
            "QToolButton#searchIconButton:pressed {"
            "background: rgba(14, 165, 233, 0.26);"
            "border: 1px solid rgba(125, 211, 252, 0.72);"
            "}"
            "QPushButton#searchToggleButton {"
            "background: rgba(217, 119, 6, 0.16);"
            "border: 1px solid rgba(245, 158, 11, 0.56);"
            "color: #FFF7ED;"
            "border-radius: 18px;"
            "padding: 12px 18px;"
            "font-size: 13px;"
            "font-weight: 700;"
            "}"
            "QPushButton#searchToggleButton:hover { background: rgba(217, 119, 6, 0.24); }"
            "QPushButton#searchToggleButton:pressed, QPushButton#searchToggleButton[pressedFeedback=\"true\"] {"
            "background: rgba(14, 165, 233, 0.28);"
            "border: 1px solid rgba(125, 211, 252, 0.74);"
            "color: #F8FAFC;"
            "}"
            "QPushButton#searchModeButton {"
            "background: rgba(255, 255, 255, 0.05);"
            "border: 1px solid rgba(255, 255, 255, 0.14);"
            "color: #D7E0EE;"
            "border-radius: 14px;"
            "padding: 8px 12px;"
            "font-size: 12px;"
            "font-weight: 700;"
            "}"
            "QPushButton#searchModeButton:checked {"
            "background: rgba(56, 189, 248, 0.20);"
            "border: 1px solid rgba(56, 189, 248, 0.78);"
            "color: #F8FAFC;"
            "}"
            "QPushButton#searchModeButton:pressed, QPushButton#searchModeButton[pressedFeedback=\"true\"] {"
            "background: rgba(14, 165, 233, 0.24);"
            "border: 1px solid rgba(125, 211, 252, 0.70);"
            "color: #F8FAFC;"
            "}"
            "QCheckBox { color: #D7E0EE; spacing: 8px; }"
            "QCheckBox::indicator {"
            "width: 18px; height: 18px;"
            "border-radius: 6px;"
            "border: 1px solid rgba(255, 255, 255, 24);"
            "background: rgba(8, 18, 32, 208);"
            "}"
            "QCheckBox::indicator:checked {"
            f"background: {action_orange};"
            "border: none;"
            "}"
            "QHeaderView::section {"
            "background: transparent;"
            "color: #94A3B8;"
            "padding: 12px 10px;"
            "border: none;"
            "font-size: 11px;"
            "font-weight: 700;"
            "}"
            "QTableWidget {"
            "alternate-background-color: rgba(255, 255, 255, 0.02);"
            "gridline-color: rgba(255, 255, 255, 0.04);"
            "show-decoration-selected: 1;"
            "}"
            "QTableWidget::item {"
            "padding: 8px;"
            "border-bottom: 1px solid rgba(255, 255, 255, 0.04);"
            "}"
            "QListWidget {"
            "background: rgba(8, 18, 32, 208);"
            "color: #F8FAFC;"
            "border: 1px solid rgba(255, 255, 255, 20);"
            "border-radius: 18px;"
            "padding: 8px;"
            "outline: 0;"
            "alternate-background-color: rgba(255, 255, 255, 0.025);"
            "}"
            "QListWidget::item {"
            "min-height: 34px;"
            "padding: 8px 12px;"
            "border-radius: 12px;"
            "border-bottom: 1px solid rgba(255, 255, 255, 0.04);"
            "}"
            "QListWidget::item:selected {"
            "background: rgba(56, 189, 248, 0.18);"
            "color: #F8FAFC;"
            "}"
            "QScrollBar:vertical {"
            "background: transparent;"
            "width: 8px;"
            "margin: 2px 2px 2px 0px;"
            "}"
            "QScrollBar::handle:vertical {"
            "background: rgba(148, 163, 184, 0.34);"
            "border-radius: 4px;"
            "min-height: 28px;"
            "}"
            "QScrollBar::handle:vertical:hover { background: rgba(148, 163, 184, 0.48); }"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical, "
            "QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {"
            "height: 0px; background: transparent;"
            "}"
            "QMenu {"
            "background: rgba(11, 23, 40, 242);"
            "color: #F8FAFC;"
            "border: 1px solid rgba(255, 255, 255, 22);"
            "border-radius: 16px;"
            "padding: 8px;"
            "}"
            "QMenu::item {"
            "color: #F8FAFC;"
            "padding: 10px 14px;"
            "border-radius: 10px;"
            "}"
            "QMenu::item:selected {"
            "background: rgba(56, 189, 248, 0.24);"
            "color: #FFFFFF;"
            "}"
            "QMenu::item:disabled { color: rgba(248, 250, 252, 0.42); }"
            "QDialog {"
            "background: rgba(11, 23, 40, 246);"
            "color: #F8FAFC;"
            "}"
            "QToolTip {"
            "background: rgba(11, 23, 40, 242);"
            "color: #F8FAFC;"
            "border: 1px solid rgba(255, 255, 255, 22);"
            "padding: 6px 8px;"
            "border-radius: 10px;"
            "}"
        )

    def _handle_escape(self):
        if hasattr(self, "_add_form_dialog") and self._add_form_dialog and self._add_form_dialog.isVisible():
            self.action_close_form()
            return
        self.show_page("home")

    def center_geometry(self, w, h):
        screen = QtGui.QGuiApplication.primaryScreen().availableGeometry()
        x = (screen.width() - w) // 2
        y = (screen.height() - h) // 2
        return QtCore.QRect(x, y, w, h)

    def _prepare_dialog(self, dialog, modal=True):
        dialog.setWindowIcon(self.windowIcon())
        dialog.setWindowFlag(QtCore.Qt.WindowContextHelpButtonHint, False)
        dialog.adjustSize()
        dialog.setGeometry(self.center_geometry(dialog.width(), dialog.height()))
        if isinstance(dialog, QtWidgets.QDialog):
            dialog.setModal(modal)
        dialog.setWindowModality(
            QtCore.Qt.ApplicationModal if modal else QtCore.Qt.NonModal
        )

    def _show_blocking_dialog(self, dialog, y_offset=18):
        del y_offset
        self._prepare_dialog(dialog, modal=True)
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    def _exec_modal_dialog(self, dialog, y_offset=18):
        self._prepare_dialog(dialog, modal=True)
        return dialog.exec()

    def update_entry_width(self, *_):
        if hasattr(self, "search_entry"):
            self.search_entry.setFixedWidth(220)

    def _current_search_mode(self):
        if hasattr(self, "search_mode_supplier") and self.search_mode_supplier.isChecked():
            return "Fornecedor"
        return "NF"

    def _supplier_names(self):
        if hasattr(self, "_supplier_names_cache"):
            return list(self._supplier_names_cache)
        suppliers = utils.load_suppliers()
        self._supplier_names_cache = [s["name"] for s in suppliers]
        return list(self._supplier_names_cache)

    def _conferente_names(self):
        if hasattr(self, "_conferente_names_cache"):
            return list(self._conferente_names_cache)
        conferentes = utils.load_conferentes()
        self._conferente_names_cache = [c["name"] for c in conferentes]
        return list(self._conferente_names_cache)

    def _get_note_by_iid(self, iid):
        return self._get_note_by_row(iid)

    def _save_notes_list(self, notes):
        if hasattr(utils, "save_all_notes"):
            utils.save_all_notes(notes)
            return True
        if hasattr(utils, "notes_path"):
            import json
            with open(utils.notes_path(), "w", encoding="utf-8") as f:
                json.dump(notes, f, ensure_ascii=False, indent=2)
            return True
        return False

    def _search_notes(self):
        termo = self.search_entry.text().strip().lower()
        if not termo:
            self.refresh_table()
            return

        filtro_tipo = self._current_search_mode()
        notes = utils.load_notes()
        notes = self._apply_filters(notes)

        if filtro_tipo in ("NF", "Nota Fiscal"):
            notes = [n for n in notes if termo in str(n.get("nf_number", "")).lower()]
        elif filtro_tipo == "Fornecedor":
            notes = [n for n in notes if termo in str(n.get("fornecedor_name", "")).lower()]

        self._populate_table(notes)

    def _ask_name_non_modal(self):
        if hasattr(self, "_name_dialog") and self._name_dialog.isVisible():
            return

        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Identificacao")
        dialog.setFixedSize(300, 150)
        layout = QtWidgets.QVBoxLayout(dialog)

        layout.addWidget(QtWidgets.QLabel("Digite seu nome:", dialog))
        entry = QtWidgets.QLineEdit(dialog)
        style_text_field(entry, center=True)
        layout.addWidget(entry)

        btn = QtWidgets.QPushButton("Salvar", dialog)
        layout.addWidget(btn)

        def salvar():
            name = entry.text().strip() or "Usuario"
            resp = utils.supabase.table("users").insert({"mac": self.mac, "name": name}).execute()
            if resp.data:
                self.user = resp.data[0]
            dialog.accept()

        btn.clicked.connect(salvar)
        entry.returnPressed.connect(salvar)
        entry.setFocus()
        self._name_dialog = dialog
        self._show_blocking_dialog(dialog)

    def show_add_form(self):
        dialog = self._ensure_add_form_window()
        suppliers = self._supplier_names()
        conferentes = self._conferente_names()
        self.combobox_supplier.clear()
        self.combobox_supplier.addItems(suppliers)
        if hasattr(self, "combobox_supplier"):
            self.combobox_supplier.setCurrentIndex(0 if self.combobox_supplier.count() else -1)
        self.combo_conferente.clear()
        self.combo_conferente.addItems(conferentes)
        if hasattr(self, "combo_conferente"):
            self.combo_conferente.setCurrentIndex(0 if self.combo_conferente.count() else -1)
        self.entry_date.setDate(QtCore.QDate.currentDate())
        self.entry_date_emissao.setDate(QtCore.QDate.currentDate())
        self.combo_cnpj.setCurrentIndex(0)
        self.entry_nf.clear()
        self._show_blocking_dialog(dialog, y_offset=24)
        self.entry_nf.setFocus(QtCore.Qt.OtherFocusReason)

    def show_manage_suppliers(self):
        self.refresh_suppliers_listbox()
        dialog = self._ensure_suppliers_dialog()
        self._show_blocking_dialog(dialog, y_offset=20)
        self.supplier_name_entry.setFocus(QtCore.Qt.OtherFocusReason)

    def show_manage_conferentes(self):
        self.refresh_conferentes_listbox()
        dialog = self._ensure_conferentes_dialog()
        self._show_blocking_dialog(dialog, y_offset=20)
        self.conf_name_entry.setFocus(QtCore.Qt.OtherFocusReason)

    def on_close(self):
        self.close()

    def _setup_tooltip_support(self):
        pass

    def _bind_search_suggestions(self):
        self.search_model = QtCore.QStringListModel([])
        self.search_completer = QtWidgets.QCompleter(self.search_model, self.search_entry)
        self.search_completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.search_completer.setFilterMode(QtCore.Qt.MatchContains)
        self.search_completer.activated.connect(self._select_suggestion)
        self.search_entry.setCompleter(self.search_completer)
        self.search_suggest_timer = QtCore.QTimer(self)
        self.search_suggest_timer.setSingleShot(True)
        self.search_suggest_timer.setInterval(160)
        self.search_suggest_timer.timeout.connect(self._update_suggestions)
        self.search_entry.textEdited.connect(lambda _text: self.search_suggest_timer.start())
        self.search_entry.installEventFilter(self)

    def _update_suggestions(self):
        termo = self.search_entry.text().strip().lower()
        filtro_tipo = self._current_search_mode()

        if len(termo) < 2:
            self.search_model.setStringList([])
            return

        notes = list(getattr(self, "last_visible_notes", []))
        if not notes:
            notes = utils.load_notes()
            notes = self._apply_filters(notes)

        if filtro_tipo in ("NF", "Nota Fiscal"):
            valores = [str(n.get("nf_number", "")) for n in notes]
        else:
            valores = [str(n.get("fornecedor_name", "")) for n in notes]

        sugestoes = sorted(set([v for v in valores if termo in v.lower()]))[:8]
        self.search_model.setStringList(sugestoes)

    def _select_suggestion(self, value):
        self.search_entry.setText(value)
        self._search_notes()

    def eventFilter(self, obj, event):
        if obj is self.search_entry and event.type() == QtCore.QEvent.KeyPress:
            if event.key() == QtCore.Qt.Key_Tab:
                self._handle_autocomplete()
                return True
        return super().eventFilter(obj, event)

    def closeEvent(self, event):
        utils.diagnostic_log("app_close_event")
        event.accept()

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("Fusion")
    utils.install_global_exception_hook()
    utils.diagnostic_log("app_main_start", argv=sys.argv)
    window = EstoqueApp()
    utils.check_for_updates(window)
    window.showMaximized()
    result = app.exec()
    utils.diagnostic_log("app_exec_finished", result=result)
    sys.exit(result)
