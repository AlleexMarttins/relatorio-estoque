import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtCore, QtWidgets

from system.conferentes_section import ConferentesMixin
from system.forms_section import FormsMixin
from system.suppliers_section import SuppliersMixin
from system.table_section import TableMixin
from system.ui_components import Toast


class FormHost(QtWidgets.QMainWindow, FormsMixin):
    def show_quick_supplier_dialog(self):
        pass

    def show_quick_conferente_dialog(self):
        pass

    def action_close_form(self):
        pass


class ConferenceHost(QtWidgets.QMainWindow, TableMixin):
    def __init__(self, note):
        super().__init__()
        self.note = note
        self.updated_fields = None
        self.refresh_count = 0

    def _get_note_by_row(self, _row):
        return self.note

    def _conferente_names(self):
        return ["Ana"]

    def _update_note_fields(self, _note, fields):
        self.updated_fields = fields
        self.note.update(fields)
        return True

    def refresh_table(self, *_args, **_kwargs):
        self.refresh_count += 1

    def _exec_modal_dialog(self, dialog, y_offset=18):
        del y_offset
        confirm = next(
            button
            for button in dialog.findChildren(QtWidgets.QPushButton)
            if button.text() == "Confirmar"
        )
        QtCore.QTimer.singleShot(0, confirm.click)
        return dialog.exec()


class ConferentesHost(QtWidgets.QMainWindow, ConferentesMixin):
    pass


class SuppliersHost(QtWidgets.QMainWindow, SuppliersMixin):
    pass


class UiStabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def test_add_form_keeps_escape_shortcut_alive(self):
        host = FormHost()
        dialog = host._ensure_add_form_window()

        self.assertIs(dialog._escape_shortcut.parent(), dialog)
        self.assertIs(host._ensure_add_form_window(), dialog)
        dialog.force_close()
        host.close()

    def test_management_dialogs_keep_escape_shortcuts_alive(self):
        hosts_and_dialogs = (
            (ConferentesHost(), "_ensure_conferentes_dialog"),
            (SuppliersHost(), "_ensure_suppliers_dialog"),
        )
        for host, factory_name in hosts_and_dialogs:
            dialog = getattr(host, factory_name)()
            self.assertIs(dialog._escape_shortcut.parent(), dialog)
            dialog.close()
            host.close()

    def test_mark_conferido_updates_and_closes_dialog(self):
        host = ConferenceHost(
            {"id": "note-1", "nf_number": "123", "conferido": False}
        )
        with patch.object(QtWidgets.QMessageBox, "information", return_value=0):
            host._mark_conferido(0)

        self.assertEqual(
            host.updated_fields,
            {
                "conferido": True,
                "conferido_por": "Ana",
                "conferido_em": QtCore.QDate.currentDate().toString("dd-MM-yyyy"),
            },
        )
        self.assertEqual(host.refresh_count, 1)
        host.close()

    def test_unmark_conferido_updates_without_dialog(self):
        host = ConferenceHost(
            {"id": "note-2", "nf_number": "456", "conferido": True}
        )
        with (
            patch.object(
                QtWidgets.QMessageBox,
                "question",
                return_value=QtWidgets.QMessageBox.Yes,
            ),
            patch.object(QtWidgets.QMessageBox, "information", return_value=0),
        ):
            host._mark_conferido(0)

        self.assertEqual(
            host.updated_fields,
            {"conferido": False, "conferido_por": None, "conferido_em": None},
        )
        self.assertEqual(host.refresh_count, 1)
        host.close()

    def test_toast_uses_window_owned_status_bar(self):
        host = QtWidgets.QMainWindow()
        Toast(host, "Operacao concluida", timeout_ms=100)

        self.assertEqual(host.statusBar().currentMessage(), "Operacao concluida")
        self.assertIs(host.statusBar().parent(), host)
        host.close()


if __name__ == "__main__":
    unittest.main()
