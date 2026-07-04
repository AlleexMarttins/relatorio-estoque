from PySide6 import QtCore, QtGui, QtWidgets

import utils_estoque as utils
from system.ui_components import make_label, make_panel, style_button, style_combo_field, style_text_field


class ConferentesMixin:
    def _ensure_conferentes_dialog(self):
        if hasattr(self, "_conferentes_dialog") and self._conferentes_dialog:
            return self._conferentes_dialog

        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Conferentes")
        dialog.setFixedSize(460, 640)

        layout = QtWidgets.QVBoxLayout(dialog)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(0)

        body = QtWidgets.QWidget(dialog)
        self._build_manage_conferentes(body)
        layout.addWidget(body)

        dialog._escape_shortcut = QtGui.QShortcut(
            QtGui.QKeySequence(QtCore.Qt.Key_Escape),
            dialog,
        )
        dialog._escape_shortcut.activated.connect(dialog.close)
        self._conferentes_dialog = dialog
        return dialog

    def _sync_conferente_controls(self):
        if hasattr(self, "_conferente_names_cache"):
            del self._conferente_names_cache
        conferente_names = self._conferente_names()
        if hasattr(self, "combo_conferente"):
            current_text = self.combo_conferente.currentText()
            self.combo_conferente.clear()
            self.combo_conferente.addItems(conferente_names)
            if current_text:
                index = self.combo_conferente.findText(current_text)
                if index >= 0:
                    self.combo_conferente.setCurrentIndex(index)

        if hasattr(self, "filter_conferido_por_cb"):
            current_filter = self.filter_conferido_por_cb.currentText()
            self.filter_conferido_por_cb.clear()
            self.filter_conferido_por_cb.addItems(["Todos"] + conferente_names)
            if current_filter:
                index = self.filter_conferido_por_cb.findText(current_filter)
                if index >= 0:
                    self.filter_conferido_por_cb.setCurrentIndex(index)

        if hasattr(self, "filter_recebido_cb"):
            current_received = self.filter_recebido_cb.currentText()
            self.filter_recebido_cb.clear()
            self.filter_recebido_cb.addItems(["Todos"] + conferente_names)
            if current_received:
                index = self.filter_recebido_cb.findText(current_received)
                if index >= 0:
                    self.filter_recebido_cb.setCurrentIndex(index)

    def _build_manage_conferentes(self, parent):
        layout = QtWidgets.QVBoxLayout(parent)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        hero_card = make_panel(parent, "surface")
        hero_layout = QtWidgets.QVBoxLayout(hero_card)
        hero_layout.setContentsMargins(16, 16, 16, 16)
        hero_layout.setSpacing(4)
        hero_layout.addWidget(make_label(hero_card, "Conferentes", hero=True, anchor="center"), 0, QtCore.Qt.AlignCenter)
        layout.addWidget(hero_card)

        list_card = make_panel(parent, "surface")
        list_layout = QtWidgets.QVBoxLayout(list_card)
        list_layout.setContentsMargins(16, 16, 16, 16)
        list_layout.setSpacing(10)
        list_layout.addWidget(
            make_label(list_card, "Lista de conferentes", font=("Segoe UI", 12, "bold"), anchor="center"),
            0,
            QtCore.Qt.AlignCenter,
        )

        self.conf_box = QtWidgets.QListWidget(list_card)
        self.conf_box.setObjectName("conferentesList")
        self.conf_box.setAlternatingRowColors(True)
        self.conf_box.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.conf_box.setFocusPolicy(QtCore.Qt.NoFocus)
        list_layout.addWidget(self.conf_box)
        layout.addWidget(list_card, 1)

        editor_card = make_panel(parent, "surface")
        editor_layout = QtWidgets.QVBoxLayout(editor_card)
        editor_layout.setContentsMargins(16, 16, 16, 16)
        editor_layout.setSpacing(10)
        editor_layout.addWidget(
            make_label(editor_card, "Novo conferente", font=("Segoe UI", 12, "bold"), anchor="center"),
            0,
            QtCore.Qt.AlignCenter,
        )

        self.conf_name_entry = QtWidgets.QLineEdit(editor_card)
        self.conf_name_entry.setPlaceholderText("Digite o conferente")
        style_text_field(self.conf_name_entry, center=True, width=280)
        editor_layout.addWidget(self.conf_name_entry, 0, QtCore.Qt.AlignHCenter)

        btns = QtWidgets.QHBoxLayout()
        btns.setContentsMargins(0, 0, 0, 0)
        btns.setSpacing(10)
        btns.addStretch(1)
        btn_add = QtWidgets.QPushButton("Adicionar", parent)
        style_button(btn_add, accent=True)
        btn_add.setFixedWidth(132)
        btn_add.clicked.connect(self.add_conferente)
        btn_remove = QtWidgets.QPushButton("Remover", parent)
        style_button(btn_remove, quiet=True)
        btn_remove.setFixedWidth(132)
        btn_remove.clicked.connect(self.remove_conferente)
        btns.addWidget(btn_add)
        btns.addWidget(btn_remove)
        btns.addStretch(1)
        editor_layout.addLayout(btns)
        layout.addWidget(editor_card)

        self.refresh_conferentes_listbox()

    def refresh_conferentes_listbox(self):
        conferentes = utils.load_conferentes()
        try:
            utils.reindex_conferentes()
            conferentes = utils.load_conferentes()
        except Exception:
            pass
        if hasattr(self, "conf_box"):
            self.conf_box.clear()
            if conferentes:
                for conferente in conferentes:
                    item = QtWidgets.QListWidgetItem(str(conferente.get("name") or ""))
                    item.setTextAlignment(QtCore.Qt.AlignCenter)
                    self.conf_box.addItem(item)
            else:
                item = QtWidgets.QListWidgetItem("Nenhum conferente cadastrado.")
                item.setTextAlignment(QtCore.Qt.AlignCenter)
                item.setFlags(QtCore.Qt.NoItemFlags)
                self.conf_box.addItem(item)

    def add_conferente(self):
        name = self.conf_name_entry.text().strip()
        if not name:
            QtWidgets.QMessageBox.warning(self, "Aviso", "Digite o nome do conferente.")
            return
        try:
            utils.add_conferente(name)
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Erro", f"Nao foi possivel adicionar o conferente.\n\n{exc}")
            return
        self.conf_name_entry.clear()
        self.refresh_conferentes_listbox()
        self._sync_conferente_controls()

    def show_quick_conferente_dialog(self):
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Novo conferente")
        dialog.setModal(True)
        dialog.setFixedSize(360, 180)
        layout = QtWidgets.QVBoxLayout(dialog)

        layout.addWidget(make_label(dialog, "Cadastrar Conferente", hero=True, anchor="center"))
        entry = QtWidgets.QLineEdit(dialog)
        entry.setPlaceholderText("Digite o conferente")
        style_text_field(entry, center=True, width=220)
        layout.addWidget(entry, 0, QtCore.Qt.AlignHCenter)

        btn_add = QtWidgets.QPushButton("Adicionar", dialog)
        style_button(btn_add, accent=True)
        btn_add.setFixedWidth(132)
        layout.addWidget(btn_add, 0, QtCore.Qt.AlignHCenter)

        def submit():
            name = entry.text().strip()
            if not name:
                QtWidgets.QMessageBox.warning(self, "Aviso", "Digite o nome do conferente.")
                return
            try:
                utils.add_conferente(name)
            except Exception as exc:
                QtWidgets.QMessageBox.critical(self, "Erro", f"Nao foi possivel adicionar o conferente.\n\n{exc}")
                return
            self.refresh_conferentes_listbox()
            self._sync_conferente_controls()
            if hasattr(self, "combo_conferente"):
                idx = self.combo_conferente.findText(name)
                if idx >= 0:
                    self.combo_conferente.setCurrentIndex(idx)
            dialog.accept()

        btn_add.clicked.connect(submit)
        entry.returnPressed.connect(submit)
        entry.setFocus()
        self._exec_modal_dialog(dialog)

    def remove_conferente(self):
        conferentes = utils.load_conferentes()
        if not conferentes:
            QtWidgets.QMessageBox.information(self, "Info", "Nenhum conferente cadastrado.")
            return

        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Remover Conferente")
        dialog.setModal(True)
        dialog.setFixedSize(360, 160)
        layout = QtWidgets.QVBoxLayout(dialog)

        layout.addWidget(make_label(dialog, "Selecione o conferente para remover:"))

        combo = QtWidgets.QComboBox(dialog)
        combo.addItems([c["name"] for c in conferentes])
        style_combo_field(combo, center=True)
        layout.addWidget(combo)

        btn_remove = QtWidgets.QPushButton("Remover", dialog)
        style_button(btn_remove, accent=True)
        layout.addWidget(btn_remove)

        def confirm_remove():
            val = combo.currentText()
            if not val:
                return

            conferentes = utils.load_conferentes()
            conf = next((c for c in conferentes if c["name"] == val), None)
            if not conf:
                QtWidgets.QMessageBox.critical(self, "Erro", "Conferente nao encontrado.")
                return

            result = utils.remove_conferente(conf["id"])
            if isinstance(result, dict) and result.get("error") == "linked_notes":
                notas = ", ".join([str(n["nf_number"]) for n in result["notes"]])
                QtWidgets.QMessageBox.warning(
                    self,
                    "Conferente vinculado",
                    f"Nao e possivel remover o conferente '{val}' pois ele esta vinculado "
                    f"as seguintes notas:\n\n{notas}\n\n"
                    "Troque o conferente nessas notas antes de remove-lo.",
                )
                return

            try:
                utils.reindex_conferentes()
            except Exception:
                pass

            self.refresh_conferentes_listbox()
            self._sync_conferente_controls()
            dialog.accept()
            QtWidgets.QMessageBox.information(self, "Sucesso", "Conferente removido com sucesso.")

        btn_remove.clicked.connect(confirm_remove)
        self._exec_modal_dialog(dialog)
