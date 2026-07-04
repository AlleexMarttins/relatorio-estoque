from datetime import datetime

from PySide6 import QtCore, QtGui, QtWidgets

import utils_estoque as utils
from system.ui_components import (
    CenteredComboBox,
    ClickableDateEdit,
    Toast,
    make_label,
    make_panel,
    style_button,
    style_combo_field,
    style_date_field,
    style_text_field,
)


class AddFormDialog(QtWidgets.QDialog):
    def __init__(self, owner):
        super().__init__(owner)
        self._owner = owner
        self._allow_close = False
        self._confirm_pending = False

    def force_close(self):
        self._allow_close = True
        self._confirm_pending = False
        self.close()
        self._allow_close = False

    def closeEvent(self, event):
        if self._allow_close:
            event.accept()
            return

        event.ignore()
        if not self._confirm_pending:
            self._confirm_pending = True
            QtCore.QTimer.singleShot(0, self._request_close_confirmation)

    def _request_close_confirmation(self):
        self._confirm_pending = False
        if self.isVisible():
            self._owner.action_close_form()


class FormsMixin:
    ADD_FORM_LABEL_WIDTH = 112
    ADD_FORM_FIELD_WIDTH = 160
    ADD_FORM_SUPPLIER_FIELD_WIDTH = 160
    ADD_FORM_CNPJ_FIELD_WIDTH = 160
    ADD_FORM_FIELD_COLUMN_WIDTH = 160
    ADD_FORM_BUTTON_WIDTH = 120
    ADD_FORM_FIELD_HEIGHT = 46
    ADD_FORM_PLUS_SIZE = 36

    def _close_add_form_window(self):
        if hasattr(self, "_add_form_dialog") and self._add_form_dialog and self._add_form_dialog.isVisible():
            if hasattr(self._add_form_dialog, "force_close"):
                self._add_form_dialog.force_close()
            else:
                self._add_form_dialog.close()
            return True
        return False

    def _ensure_add_form_window(self):
        if hasattr(self, "_add_form_dialog") and self._add_form_dialog:
            return self._add_form_dialog

        dialog = AddFormDialog(self)
        dialog.setWindowFlag(QtCore.Qt.Window, True)
        dialog.setModal(True)
        dialog.setWindowTitle("Adição de NF")
        dialog.setWindowIcon(self.windowIcon())
        dialog.setFixedSize(410, 490)

        layout = QtWidgets.QVBoxLayout(dialog)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(0)

        body = QtWidgets.QWidget(dialog)
        self._build_add_form(body)
        layout.addWidget(body)

        dialog._escape_shortcut = QtGui.QShortcut(
            QtGui.QKeySequence(QtCore.Qt.Key_Escape),
            dialog,
        )
        dialog._escape_shortcut.activated.connect(self.action_close_form)
        self._add_form_dialog = dialog
        return dialog

    def on_add_ok(self):
        try:
            nf = self.entry_nf.text().strip()
            nf = str(nf).lstrip("0")

            if not nf:
                QtWidgets.QMessageBox.warning(self, "Aviso", "Preencha o campo NF.")
                return

            fornecedor = self.combobox_supplier.currentText().strip()
            conferente = self.combo_conferente.currentText().strip()

            if not fornecedor or not conferente:
                QtWidgets.QMessageBox.warning(self, "Aviso", "Selecione fornecedor e conferente.")
                return

            data_chegada = self.entry_date.date().toString("dd-MM-yyyy")
            data_emissao = self.entry_date_emissao.date().toString("dd-MM-yyyy")

            try:
                datetime.strptime(data_chegada, "%d-%m-%Y")
                datetime.strptime(data_emissao, "%d-%m-%Y")
            except Exception:
                QtWidgets.QMessageBox.warning(self, "Aviso", "Data invalida. Use DD-MM-YYYY.")
                return

            cnpj = (self.combo_cnpj.currentData() or self.combo_cnpj.currentText()).strip()

            suppliers = utils.load_suppliers()
            supplier = next((x for x in suppliers if x["name"] == fornecedor), {"id": None, "name": fornecedor})
            conferentes = utils.load_conferentes()
            conferente_data = next((x for x in conferentes if x["name"] == conferente), {"id": None, "name": conferente})
            user_name = self.user.get("name") if isinstance(self.user, dict) else "Desconhecido"

            note = {
                "nf_number": nf,
                "fornecedor_id": supplier.get("id"),
                "fornecedor_name": supplier.get("name"),
                "data_chegada": data_chegada,
                "data_emissao": data_emissao,
                "cnpj": cnpj,
                "conferente_id": conferente_data.get("id"),
                "conferente_name": conferente_data.get("name"),
                "recebido_por": conferente_data.get("name"),
                "created_at": datetime.now().isoformat(),
                "conferido": False,
                "conferido_por": None,
                "conferido_em": None,
                "modified_by": user_name if user_name != "Desconhecido" else None,
            }

            notes = utils.load_notes()
            nf_number = nf.strip()
            if any(str(n.get("nf_number")) == nf_number for n in notes):
                QtWidgets.QMessageBox.warning(self, "Duplicado", f"A nota {nf_number} ja existe!")
                return

            saved_notes = utils.save_note(note)
            saved_note = next(
                (
                    item
                    for item in saved_notes
                    if str(item.get("nf_number")) == str(note.get("nf_number"))
                ),
                note,
            )
            utils.acknowledge_note_change(saved_note)
            self.refresh_table()
            QtWidgets.QMessageBox.information(self, "Sucesso", "Nota salva com sucesso.")
            Toast(self, f"Nota {note.get('nf_number')} adicionada por {user_name}")
            if not self._close_add_form_window():
                self.show_page("home")
        except Exception as exc:
            utils.log_exception("Falha ao criar nota fiscal", exc)
            QtWidgets.QMessageBox.critical(
                self,
                "Erro ao criar nota",
                "Nao foi possivel salvar a nota. "
                f"O detalhe foi salvo em:\n{utils.runtime_log_path()}",
            )

    def action_close_form(self):
        if not self.settings.get("ask_on_close", True):
            if not self._close_add_form_window():
                self.show_page("home")
            return

        if getattr(self, "_confirm_close_dialog", None) and self._confirm_close_dialog.isVisible():
            self._confirm_close_dialog.raise_()
            self._confirm_close_dialog.activateWindow()
            return

        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Confirmar")
        dialog.setModal(True)
        dialog.setFixedSize(360, 160)
        layout = QtWidgets.QVBoxLayout(dialog)

        message = make_label(dialog, "Tem certeza que deseja cancelar?", anchor="center")
        message.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(message, 0, QtCore.Qt.AlignCenter)
        dont_ask = QtWidgets.QCheckBox("N\u00e3o me pergunte novamente", dialog)
        layout.addWidget(dont_ask)

        btns = QtWidgets.QHBoxLayout()
        btn_yes = QtWidgets.QPushButton("Sim", dialog)
        style_button(btn_yes, accent=True)
        btn_no = QtWidgets.QPushButton("N\u00e3o", dialog)
        style_button(btn_no, quiet=True)
        btns.addWidget(btn_yes)
        btns.addWidget(btn_no)
        layout.addLayout(btns)

        def on_yes():
            if dont_ask.isChecked():
                self.settings["ask_on_close"] = False
                utils.save_settings(self.settings)
            dialog.accept()
            if not self._close_add_form_window():
                self.show_page("home")

        btn_yes.clicked.connect(on_yes)
        btn_no.clicked.connect(dialog.reject)
        self._confirm_close_dialog = dialog
        self._exec_modal_dialog(dialog)
        self._confirm_close_dialog = None

    def _build_centered_field(self, parent, widget):
        wrapper = QtWidgets.QWidget(parent)
        wrapper.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        row = QtWidgets.QHBoxLayout(wrapper)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)
        row.addStretch(1)
        row.addWidget(widget, 0, QtCore.Qt.AlignCenter)
        row.addStretch(1)
        return wrapper

    def _build_inline_add_row(self, parent, combo, add_handler):
        wrapper = QtWidgets.QWidget(parent)
        wrapper.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        row = QtWidgets.QHBoxLayout(wrapper)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        row.addStretch(1)
        row.addWidget(combo, 0, QtCore.Qt.AlignCenter)

        btn_add = QtWidgets.QPushButton("+", wrapper)
        btn_add.setFixedSize(42, 42)
        btn_add.setToolTip("Adicionar novo cadastro")
        style_button(btn_add, accent=True)
        btn_add.clicked.connect(add_handler)
        row.addWidget(btn_add, 0, QtCore.Qt.AlignCenter)
        row.addStretch(1)
        return wrapper

    def _add_stack_field(self, layout, parent, title, widget):
        layout.addWidget(make_label(parent, title, muted=True, anchor="center"), 0, QtCore.Qt.AlignCenter)
        layout.addWidget(widget, 0, QtCore.Qt.AlignCenter)

    def _make_form_label(self, parent, text):
        label = make_label(parent, text, muted=True)
        label.setFixedWidth(self.ADD_FORM_LABEL_WIDTH)
        label.setFixedHeight(self.ADD_FORM_FIELD_HEIGHT)
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        return label

    def _add_form_grid_row(self, layout, row, parent, title, field, add_handler=None):
        layout.addWidget(self._make_form_label(parent, title), row, 0)
        layout.addWidget(field, row, 1, QtCore.Qt.AlignCenter)

        if add_handler:
            btn_add = QtWidgets.QPushButton("+", parent)
            btn_add.setFixedSize(self.ADD_FORM_PLUS_SIZE, self.ADD_FORM_PLUS_SIZE)
            btn_add.setToolTip("Adicionar novo cadastro")
            style_button(btn_add, accent=True)
            btn_add.clicked.connect(add_handler)
            layout.addWidget(btn_add, row, 2, QtCore.Qt.AlignCenter)
        else:
            spacer = QtWidgets.QWidget(parent)
            spacer.setFixedSize(self.ADD_FORM_PLUS_SIZE, self.ADD_FORM_PLUS_SIZE)
            layout.addWidget(spacer, row, 2)

    def _make_form_grid(self, parent):
        grid_shell = QtWidgets.QWidget(parent)
        grid_shell.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        grid_layout = QtWidgets.QGridLayout(grid_shell)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        grid_layout.setHorizontalSpacing(8)
        grid_layout.setVerticalSpacing(6)
        grid_layout.setColumnMinimumWidth(1, self.ADD_FORM_FIELD_COLUMN_WIDTH)
        return grid_shell, grid_layout

    def _build_add_form(self, parent):
        layout = QtWidgets.QVBoxLayout(parent)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        hero_card = make_panel(parent, "surface")
        hero_layout = QtWidgets.QVBoxLayout(hero_card)
        hero_layout.setContentsMargins(14, 10, 14, 10)
        hero_layout.setSpacing(0)
        hero_layout.addWidget(make_label(hero_card, "Adi\u00e7\u00e3o de NF", hero=True, anchor="center"), 0, QtCore.Qt.AlignCenter)
        layout.addWidget(hero_card)

        identity_card = make_panel(parent, "surface")
        identity_layout = QtWidgets.QVBoxLayout(identity_card)
        identity_layout.setContentsMargins(14, 10, 14, 10)
        identity_layout.setSpacing(0)
        identity_grid_shell, identity_grid = self._make_form_grid(identity_card)

        self.entry_nf = QtWidgets.QLineEdit(identity_card)
        nf_validator = QtGui.QRegularExpressionValidator(QtCore.QRegularExpression("[0-9.]*"), self.entry_nf)
        self.entry_nf.setValidator(nf_validator)
        self.entry_nf.setPlaceholderText("Ex.: 123456")
        self.entry_nf.setMaxLength(20)
        self.entry_nf.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        style_text_field(self.entry_nf, center=True, width=self.ADD_FORM_FIELD_WIDTH, height=self.ADD_FORM_FIELD_HEIGHT)
        self._add_form_grid_row(identity_grid, 0, identity_card, "NF:", self.entry_nf)

        self.combobox_supplier = CenteredComboBox(identity_card)
        self.combobox_supplier.setProperty("supplierField", True)
        supplier_font = self.combobox_supplier.font()
        supplier_font.setPointSize(9)
        self.combobox_supplier.setFont(supplier_font)
        self.combobox_supplier.setFixedWidth(self.ADD_FORM_SUPPLIER_FIELD_WIDTH)
        self.combobox_supplier.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        style_combo_field(self.combobox_supplier, center=True, height=self.ADD_FORM_FIELD_HEIGHT)
        self._add_form_grid_row(
            identity_grid,
            1,
            identity_card,
            "Fornecedor:",
            self.combobox_supplier,
            self.show_quick_supplier_dialog,
        )

        self.combo_cnpj = CenteredComboBox(identity_card)
        self.combo_cnpj.addItem("Eletr\u00f4nica Horizonte", "EH")
        self.combo_cnpj.addItem("MVA", "MVA")
        cnpj_font = self.combo_cnpj.font()
        cnpj_font.setPointSize(9)
        self.combo_cnpj.setFont(cnpj_font)
        self.combo_cnpj.setProperty("minimumTextPointSize", 8)
        self.combo_cnpj.setFixedWidth(self.ADD_FORM_CNPJ_FIELD_WIDTH)
        self.combo_cnpj.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        style_combo_field(self.combo_cnpj, center=True, height=self.ADD_FORM_FIELD_HEIGHT)
        self._add_form_grid_row(identity_grid, 2, identity_card, "CNPJ:", self.combo_cnpj)
        identity_layout.addWidget(identity_grid_shell, 0, QtCore.Qt.AlignCenter)
        layout.addWidget(identity_card)

        schedule_card = make_panel(parent, "surface")
        schedule_layout = QtWidgets.QVBoxLayout(schedule_card)
        schedule_layout.setContentsMargins(14, 10, 14, 10)
        schedule_layout.setSpacing(0)
        schedule_grid_shell, schedule_grid = self._make_form_grid(schedule_card)

        self.entry_date = ClickableDateEdit(schedule_card)
        style_date_field(
            self.entry_date,
            width=self.ADD_FORM_FIELD_WIDTH,
            height=self.ADD_FORM_FIELD_HEIGHT,
            display_format="dd/MM/yyyy",
        )
        self.entry_date.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self.entry_date.setDate(QtCore.QDate.currentDate())
        self._add_form_grid_row(schedule_grid, 0, schedule_card, "Chegada:", self.entry_date)

        self.entry_date_emissao = ClickableDateEdit(schedule_card)
        style_date_field(
            self.entry_date_emissao,
            width=self.ADD_FORM_FIELD_WIDTH,
            height=self.ADD_FORM_FIELD_HEIGHT,
            display_format="dd/MM/yyyy",
        )
        self.entry_date_emissao.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self.entry_date_emissao.setDate(QtCore.QDate.currentDate())
        self._add_form_grid_row(schedule_grid, 1, schedule_card, "Emissão:", self.entry_date_emissao)

        self.combo_conferente = CenteredComboBox(schedule_card)
        self.combo_conferente.setFixedWidth(self.ADD_FORM_FIELD_WIDTH)
        self.combo_conferente.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        style_combo_field(self.combo_conferente, center=True, height=self.ADD_FORM_FIELD_HEIGHT)
        self._add_form_grid_row(
            schedule_grid,
            2,
            schedule_card,
            "Recebida por:",
            self.combo_conferente,
            self.show_quick_conferente_dialog,
        )
        schedule_layout.addWidget(schedule_grid_shell, 0, QtCore.Qt.AlignCenter)

        layout.addWidget(schedule_card)

        btns = QtWidgets.QVBoxLayout()
        btns.setContentsMargins(0, 0, 0, 0)
        btns.setSpacing(8)
        self.btn_ok = QtWidgets.QPushButton("Adicionar NF", parent)
        style_button(self.btn_ok, accent=True)
        ok_font = self.btn_ok.font()
        ok_font.setPointSize(9)
        self.btn_ok.setFont(ok_font)
        self.btn_ok.setFixedWidth(self.ADD_FORM_BUTTON_WIDTH)
        self.btn_ok.clicked.connect(self.on_add_ok)
        btns.addWidget(self.btn_ok, 0, QtCore.Qt.AlignHCenter)

        layout.addLayout(btns)
        layout.addStretch(1)
