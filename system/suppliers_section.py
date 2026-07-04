from PySide6 import QtCore, QtGui, QtWidgets

import utils_estoque as utils
from system.ui_components import make_label, make_panel, style_button, style_combo_field, style_text_field


class SuppliersMixin:
    def _ensure_suppliers_dialog(self):
        if hasattr(self, "_suppliers_dialog") and self._suppliers_dialog:
            return self._suppliers_dialog

        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Fornecedores")
        dialog.setFixedSize(460, 640)

        layout = QtWidgets.QVBoxLayout(dialog)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(0)

        body = QtWidgets.QWidget(dialog)
        self._build_manage_suppliers(body)
        layout.addWidget(body)

        dialog._escape_shortcut = QtGui.QShortcut(
            QtGui.QKeySequence(QtCore.Qt.Key_Escape),
            dialog,
        )
        dialog._escape_shortcut.activated.connect(dialog.close)
        self._suppliers_dialog = dialog
        return dialog

    def _sync_supplier_controls(self):
        if hasattr(self, "_supplier_names_cache"):
            del self._supplier_names_cache
        supplier_names = self._supplier_names()
        if hasattr(self, "combobox_supplier"):
            current_text = self.combobox_supplier.currentText()
            self.combobox_supplier.clear()
            self.combobox_supplier.addItems(supplier_names)
            if current_text:
                index = self.combobox_supplier.findText(current_text)
                if index >= 0:
                    self.combobox_supplier.setCurrentIndex(index)

        if hasattr(self, "filter_fornecedor_cb"):
            current_filter = self.filter_fornecedor_cb.currentText()
            self.filter_fornecedor_cb.clear()
            self.filter_fornecedor_cb.addItems(["Todas"] + supplier_names)
            if current_filter:
                index = self.filter_fornecedor_cb.findText(current_filter)
                if index >= 0:
                    self.filter_fornecedor_cb.setCurrentIndex(index)

    def _build_manage_suppliers(self, parent):
        layout = QtWidgets.QVBoxLayout(parent)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        hero_card = make_panel(parent, "surface")
        hero_layout = QtWidgets.QVBoxLayout(hero_card)
        hero_layout.setContentsMargins(16, 16, 16, 16)
        hero_layout.setSpacing(4)
        hero_layout.addWidget(make_label(hero_card, "Fornecedores", hero=True, anchor="center"), 0, QtCore.Qt.AlignCenter)
        layout.addWidget(hero_card)

        list_card = make_panel(parent, "surface")
        list_layout = QtWidgets.QVBoxLayout(list_card)
        list_layout.setContentsMargins(16, 16, 16, 16)
        list_layout.setSpacing(10)
        list_layout.addWidget(
            make_label(list_card, "Lista de fornecedores", font=("Segoe UI", 12, "bold"), anchor="center"),
            0,
            QtCore.Qt.AlignCenter,
        )

        self.suppliers_box = QtWidgets.QListWidget(list_card)
        self.suppliers_box.setObjectName("suppliersList")
        self.suppliers_box.setAlternatingRowColors(True)
        self.suppliers_box.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.suppliers_box.setFocusPolicy(QtCore.Qt.NoFocus)
        list_layout.addWidget(self.suppliers_box)
        layout.addWidget(list_card, 1)

        editor_card = make_panel(parent, "surface")
        editor_layout = QtWidgets.QVBoxLayout(editor_card)
        editor_layout.setContentsMargins(16, 16, 16, 16)
        editor_layout.setSpacing(10)
        editor_layout.addWidget(
            make_label(editor_card, "Novo fornecedor", font=("Segoe UI", 12, "bold"), anchor="center"),
            0,
            QtCore.Qt.AlignCenter,
        )

        self.supplier_name_entry = QtWidgets.QLineEdit(editor_card)
        self.supplier_name_entry.setPlaceholderText("Digite o fornecedor")
        style_text_field(self.supplier_name_entry, center=True, width=280)
        editor_layout.addWidget(self.supplier_name_entry, 0, QtCore.Qt.AlignCenter)

        btns = QtWidgets.QHBoxLayout()
        btns.setContentsMargins(0, 0, 0, 0)
        btns.setSpacing(10)
        btns.addStretch(1)
        btn_add = QtWidgets.QPushButton("Adicionar", parent)
        btn_add.setFixedWidth(132)
        style_button(btn_add, accent=True)
        btn_add.clicked.connect(self.add_supplier)
        btn_remove = QtWidgets.QPushButton("Remover", parent)
        btn_remove.setFixedWidth(132)
        style_button(btn_remove, quiet=True)
        btn_remove.clicked.connect(self.remove_supplier)
        btns.addWidget(btn_add)
        btns.addWidget(btn_remove)
        btns.addStretch(1)
        editor_layout.addLayout(btns)
        layout.addWidget(editor_card)

        self.refresh_suppliers_listbox()

    def refresh_suppliers_listbox(self):
        suppliers = utils.load_suppliers()
        try:
            utils.reindex_suppliers()
            suppliers = utils.load_suppliers()
        except Exception:
            pass
        if hasattr(self, "suppliers_box"):
            self.suppliers_box.clear()
            if suppliers:
                for supplier in suppliers:
                    item = QtWidgets.QListWidgetItem(str(supplier.get("name") or ""))
                    item.setTextAlignment(QtCore.Qt.AlignCenter)
                    self.suppliers_box.addItem(item)
            else:
                item = QtWidgets.QListWidgetItem("Nenhum fornecedor cadastrado.")
                item.setTextAlignment(QtCore.Qt.AlignCenter)
                item.setFlags(QtCore.Qt.NoItemFlags)
                self.suppliers_box.addItem(item)

    def add_supplier(self):
        name = self.supplier_name_entry.text().strip()
        if not name:
            QtWidgets.QMessageBox.warning(self, "Aviso", "Digite o nome do fornecedor.")
            return
        try:
            utils.add_supplier(name)
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Erro", f"Nao foi possivel adicionar o fornecedor.\n\n{exc}")
            return

        self.supplier_name_entry.clear()
        self.refresh_suppliers_listbox()
        self._sync_supplier_controls()

    def show_quick_supplier_dialog(self):
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Novo fornecedor")
        dialog.setModal(True)
        dialog.setFixedSize(360, 180)
        layout = QtWidgets.QVBoxLayout(dialog)

        layout.addWidget(make_label(dialog, "Cadastrar Fornecedor", hero=True, anchor="center"))
        entry = QtWidgets.QLineEdit(dialog)
        entry.setPlaceholderText("Digite o fornecedor")
        style_text_field(entry, center=True)
        layout.addWidget(entry)

        btn_add = QtWidgets.QPushButton("Adicionar", dialog)
        style_button(btn_add, accent=True)
        btn_add.setFixedWidth(150)
        layout.addWidget(btn_add, 0, QtCore.Qt.AlignHCenter)

        def submit():
            name = entry.text().strip()
            if not name:
                QtWidgets.QMessageBox.warning(self, "Aviso", "Digite o nome do fornecedor.")
                return
            try:
                utils.add_supplier(name)
            except Exception as exc:
                QtWidgets.QMessageBox.critical(self, "Erro", f"Nao foi possivel adicionar o fornecedor.\n\n{exc}")
                return
            self.refresh_suppliers_listbox()
            self._sync_supplier_controls()
            if hasattr(self, "combobox_supplier"):
                idx = self.combobox_supplier.findText(name)
                if idx >= 0:
                    self.combobox_supplier.setCurrentIndex(idx)
            dialog.accept()

        btn_add.clicked.connect(submit)
        entry.returnPressed.connect(submit)
        entry.setFocus()
        self._exec_modal_dialog(dialog)

    def remove_supplier(self):
        suppliers = utils.load_suppliers()
        if not suppliers:
            QtWidgets.QMessageBox.information(self, "Info", "Nenhum fornecedor cadastrado.")
            return

        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Remover Fornecedor")
        dialog.setModal(True)
        dialog.setFixedSize(360, 160)
        layout = QtWidgets.QVBoxLayout(dialog)

        layout.addWidget(make_label(dialog, "Selecione o fornecedor para remover:"))

        combo = QtWidgets.QComboBox(dialog)
        combo.addItems([s["name"] for s in suppliers])
        style_combo_field(combo, center=True)
        layout.addWidget(combo)

        btn_remove = QtWidgets.QPushButton("Remover", dialog)
        style_button(btn_remove, accent=True)
        layout.addWidget(btn_remove)

        def confirm_remove():
            val = combo.currentText()
            if not val:
                return

            suppliers = utils.load_suppliers()
            supplier = next((s for s in suppliers if s["name"] == val), None)
            if not supplier:
                QtWidgets.QMessageBox.critical(self, "Erro", "Fornecedor nao encontrado.")
                return

            result = utils.remove_supplier(supplier["id"])
            if isinstance(result, dict) and result.get("error") == "linked_notes":
                notas = ", ".join([str(n["nf_number"]) for n in result["notes"]])
                QtWidgets.QMessageBox.warning(
                    self,
                    "Fornecedor vinculado",
                    f"Nao e possivel remover o fornecedor '{val}' pois ele esta vinculado "
                    f"as seguintes notas:\n\n{notas}\n\n"
                    "Troque o fornecedor nessas notas antes de remove-lo.",
                )
                return

            try:
                utils.reindex_suppliers()
            except Exception:
                pass

            self.refresh_suppliers_listbox()
            self._sync_supplier_controls()
            dialog.accept()
            QtWidgets.QMessageBox.information(self, "Sucesso", "Fornecedor removido com sucesso.")

        btn_remove.clicked.connect(confirm_remove)
        self._exec_modal_dialog(dialog)
