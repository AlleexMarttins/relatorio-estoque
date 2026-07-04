from datetime import datetime

from PySide6 import QtCore, QtGui, QtWidgets

import utils_estoque as utils
from system.ui_components import (
    CenteredComboBox,
    ClickableDateEdit,
    MetricCard,
    PillDelegate,
    Toast,
    apply_shadow,
    make_badge,
    make_label,
    make_panel,
    style_button,
    style_combo_field,
    style_date_field,
    style_text_field,
)


class TableMixin:
    CNPJ_OPTIONS = (
        ("Eletr\u00f4nica Horizonte", "EH"),
        ("MVA", "MVA"),
    )

    def _build_table(self):
        cols = ("nf", "data", "fornecedor", "conferente", "cnpj", "conferido")
        headings = {
            "nf": "Nota Fiscal",
            "data": "Data de Chegada",
            "fornecedor": "Fornecedor",
            "conferente": "Recebida por",
            "cnpj": "CNPJ",
            "conferido": "Conferencia",
        }

        metrics_row = QtWidgets.QHBoxLayout()
        metrics_row.setContentsMargins(0, 0, 0, 0)
        metrics_row.setSpacing(14)
        self.metric_total = MetricCard(self.main_frame, "Notas em fluxo", "accent")
        self.metric_conferidas = MetricCard(self.main_frame, "Conferidas", "green")
        self.metric_pendentes = MetricCard(self.main_frame, "Pendentes", "blue")
        metrics_row.addWidget(self.metric_total, 1)
        metrics_row.addWidget(self.metric_conferidas, 1)
        metrics_row.addWidget(self.metric_pendentes, 1)
        self.main_layout.addLayout(metrics_row)

        container = make_panel(self.main_frame, "surface")
        container_layout = QtWidgets.QVBoxLayout(container)
        container_layout.setContentsMargins(18, 18, 18, 18)
        container_layout.setSpacing(14)
        apply_shadow(container, blur=30, y_offset=14, alpha=45)

        header_layout = QtWidgets.QGridLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(0)
        header_title = make_label(container, "Lista operacional", font=("Segoe UI", 16, "bold"), anchor="center")
        header_layout.addWidget(header_title, 0, 0, QtCore.Qt.AlignCenter)

        self.btn_toggle_search = QtWidgets.QToolButton(container)
        self.btn_toggle_search.setObjectName("searchIconButton")
        self.btn_toggle_search.setIcon(self._make_search_icon())
        self.btn_toggle_search.setIconSize(QtCore.QSize(20, 20))
        self.btn_toggle_search.setFixedSize(42, 42)
        self.btn_toggle_search.setToolTip("Abrir busca")
        self.btn_toggle_search.clicked.connect(self._show_search_menu)
        header_layout.addWidget(self.btn_toggle_search, 0, 0, QtCore.Qt.AlignRight | QtCore.Qt.AlignTop)
        container_layout.addLayout(header_layout)

        operational_summary = QtWidgets.QHBoxLayout()
        operational_summary.setContentsMargins(0, 0, 0, 0)
        operational_summary.setSpacing(10)
        self.operational_visible_value = self._make_operational_stat(container, "Notas visiveis", "0")
        self.operational_done_value = self._make_operational_stat(container, "Conferidas", "0")
        self.operational_scope_value = self._make_operational_stat(container, "Escopo", "Mes atual")
        operational_summary.addStretch(1)
        operational_summary.addWidget(self.operational_visible_value.parentWidget(), 0)
        operational_summary.addWidget(self.operational_done_value.parentWidget(), 0)
        operational_summary.addWidget(self.operational_scope_value.parentWidget(), 0)
        operational_summary.addStretch(1)
        container_layout.addLayout(operational_summary)

        self.table = QtWidgets.QTableWidget(0, len(cols), container)
        self.table.setHorizontalHeaderLabels([headings[c] for c in cols])
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.setSortingEnabled(False)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setWordWrap(False)
        self.table.setCornerButtonEnabled(False)
        self.table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        self.table.horizontalHeader().setDefaultAlignment(QtCore.Qt.AlignCenter)
        self.table.verticalHeader().setVisible(False)
        self.table.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._on_table_context_menu)
        self.table.cellDoubleClicked.connect(self._on_table_double_click)
        self.table.horizontalHeader().sectionClicked.connect(self._on_header_clicked)
        self.table.setItemDelegateForColumn(
            4,
            PillDelegate(
                {
                    "eh": ("#10243B", "#7DD3FC"),
                    "mva": ("#2C1B10", "#FDBA74"),
                },
                self.table,
            ),
        )
        self.table.setItemDelegateForColumn(
            5,
            PillDelegate(
                {
                    "conferida": ("#0D2B1C", "#86EFAC"),
                    "pendente": ("#172554", "#BFDBFE"),
                },
                self.table,
            ),
        )

        container_layout.addWidget(self.table)
        self.main_layout.addWidget(container, 1)
        self._sort_reverse = {i: False for i in range(len(cols))}
        self.last_visible_notes = []

    def _make_operational_stat(self, parent, title, value):
        card = QtWidgets.QFrame(parent)
        card.setProperty("summaryStat", True)
        card.setFixedSize(156 if title != "Escopo" else 188, 56)
        layout = QtWidgets.QVBoxLayout(card)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(2)

        title_label = make_label(card, title.upper(), muted=True, anchor="center")
        title_label.setProperty("summaryLabel", True)
        value_label = make_label(card, value, anchor="center")
        value_label.setProperty("summaryValue", True)
        layout.addWidget(title_label)
        layout.addWidget(value_label)
        return value_label

    def _make_search_icon(self):
        pixmap = QtGui.QPixmap(22, 22)
        pixmap.fill(QtCore.Qt.transparent)
        painter = QtGui.QPainter(pixmap)
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
        pen = QtGui.QPen(QtGui.QColor("#F8FAFC"), 2.2)
        pen.setCapStyle(QtCore.Qt.RoundCap)
        painter.setPen(pen)
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.drawEllipse(QtCore.QRectF(4, 4, 9, 9))
        painter.drawLine(QtCore.QPointF(12, 12), QtCore.QPointF(18, 18))
        painter.end()
        return QtGui.QIcon(pixmap)

    def _populate_table(self, notes):
        self.table.setRowCount(0)
        for n in notes:
            data_display = self._format_display_date(n.get("data_chegada") or n.get("created_at"))
            recebido_por = str(n.get("recebido_por") or n.get("conferente_name") or "")
            conferido_display = "Conferida" if n.get("conferido", False) else "Pendente"
            row = self.table.rowCount()
            self.table.insertRow(row)

            values = [
                str(n.get("nf_number") or ""),
                data_display,
                str(n.get("fornecedor_name") or ""),
                recebido_por,
                str(n.get("cnpj") or ""),
                conferido_display,
            ]

            for col, val in enumerate(values):
                item = QtWidgets.QTableWidgetItem(val)
                item.setTextAlignment(QtCore.Qt.AlignCenter)
                if col == 0:
                    item.setData(QtCore.Qt.UserRole, n.get("id"))

                if col == 1 and n.get("data_emissao"):
                    item.setToolTip(f"Data de emissao: {n.get('data_emissao')}")
                if col == 5 and n.get("conferido"):
                    item.setToolTip(f"{n.get('conferido_por', '?')} em {n.get('conferido_em', '?')}")

                self.table.setItem(row, col, item)

        self.table.resizeRowsToContents()
        self.update_recent_list()

    def _sort_by_column(self, col, reverse):
        data = []
        for row in range(self.table.rowCount()):
            item = self.table.item(row, col)
            val = item.text() if item else ""
            data.append((self._sort_value(val), row))

        data.sort(key=lambda t: t[0], reverse=reverse)

        rows = []
        for _, row in data:
            items = [
                self.table.item(row, c).clone() if self.table.item(row, c) else QtWidgets.QTableWidgetItem("")
                for c in range(self.table.columnCount())
            ]
            rows.append(items)

        self.table.setRowCount(0)
        for items in rows:
            row = self.table.rowCount()
            self.table.insertRow(row)
            for c, item in enumerate(items):
                self.table.setItem(row, c, item)

        self.table.resizeRowsToContents()

    def _sort_value(self, v):
        try:
            return datetime.strptime(v, "%d-%m-%Y")
        except Exception:
            try:
                return float(v.replace(".", "").replace(",", "."))
            except Exception:
                return v.lower()

    def _on_header_clicked(self, col):
        reverse = self._sort_reverse.get(col, False)
        self._sort_by_column(col, reverse)
        self._sort_reverse[col] = not reverse

    def _visible_notes(self, notes=None):
        notes = list(notes) if notes is not None else utils.load_notes()
        notes = self._apply_filters(notes)
        if not self.settings.get("visualizar_todos_meses", False):
            mes_atual = datetime.now().month
            ano_atual = datetime.now().year
            notes = [
                n
                for n in notes
                if n.get("data_chegada")
                and datetime.strptime(n["data_chegada"], "%d-%m-%Y").month == mes_atual
                and datetime.strptime(n["data_chegada"], "%d-%m-%Y").year == ano_atual
            ]
        return notes

    def refresh_table(self, notes=None):
        source_notes = list(notes) if notes is not None else utils.load_notes()
        self._all_notes_cache = list(source_notes)
        notes = self._visible_notes(source_notes)
        self.last_visible_notes = notes
        self._populate_table(notes)
        self._refresh_dashboard_metrics(notes)
        self._update_conferente_counter(notes)
        if hasattr(self, "_update_toolbar_summary"):
            conferidas = sum(1 for n in notes if n.get("conferido", False))
            self._update_toolbar_summary(len(notes), conferidas)

    def _refresh_dashboard_metrics(self, notes):
        total = len(notes)
        conferidas = sum(1 for n in notes if n.get("conferido", False))
        pendentes = max(0, total - conferidas)
        fornecedores_ativos = len({n.get("fornecedor_name") for n in notes if n.get("fornecedor_name")})
        taxa_conferencia = conferidas / total if total else 0
        carga_pendente = pendentes / total if total else 0

        self.metric_total.set_data(total, f"{fornecedores_ativos} fornecedores ativos", max(0.2, min(1.0, fornecedores_ativos / max(total, 1) if total else 0.2)))
        self.metric_conferidas.set_data(conferidas, f"{int(taxa_conferencia * 100)}% do fluxo concluido", max(0.18, taxa_conferencia if total else 0.18))
        self.metric_pendentes.set_data(pendentes, "Aguardando conferencia" if pendentes else "Fila limpa", max(0.18, carga_pendente if total else 0.18))

        if hasattr(self, "table_count_badge_label"):
            self.table_count_badge_label.setText(f"{total} linhas")

        if hasattr(self, "table_scope_badge_label"):
            if self.settings.get("visualizar_todos_meses", False):
                self.table_scope_badge_label.setText("Hist\u00f3rico anual")
            else:
                self.table_scope_badge_label.setText("M\u00eas Atual")

        if hasattr(self, "home_volume_label"):
            self.home_volume_label.setText(f"{total} notas em fluxo" if total else "Sem notas em fluxo")
        if hasattr(self, "home_status_label"):
            if pendentes:
                self.home_status_label.setText(
                    f"{pendentes} notas aguardam conferência. Exemplo: notas já recebidas, mas ainda sem marcação final de conferido."
                )
            else:
                self.home_status_label.setText(
                    "Não há notas pendentes no filtro atual. Exemplo: se 12 notas foram recebidas e as 12 já foram conferidas, a fila fica limpa."
                )

        if hasattr(self, "home_status_label"):
            if total == 0:
                self.home_status_label.setText("")
            elif pendentes:
                self.home_status_label.setText(
                    f"{pendentes} notas aguardam confer\u00eancia. Exemplo: notas j\u00e1 recebidas, mas ainda sem marca\u00e7\u00e3o final de conferido."
                )
            else:
                self.home_status_label.setText(
                    "N\u00e3o h\u00e1 notas pendentes no filtro atual. Exemplo: se 12 notas foram recebidas e as 12 j\u00e1 foram conferidas, a fila fica limpa."
                )

    def _update_conferente_counter(self, notes=None):
        notes = notes if notes is not None else self._visible_notes()
        period = getattr(self, "conference_period", "month")
        today = datetime.now().date()

        def parse_date(raw_value):
            text = str(raw_value or "")[:10]
            for fmt in ("%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y"):
                try:
                    return datetime.strptime(text, fmt).date()
                except Exception:
                    continue
            return None

        def in_period(note):
            if period == "total":
                return True
            conferido_em = parse_date(note.get("conferido_em"))
            if not conferido_em:
                return False
            if period == "day":
                return conferido_em == today
            if period == "week":
                return conferido_em.isocalendar()[:2] == today.isocalendar()[:2]
            return conferido_em.month == today.month and conferido_em.year == today.year

        period_labels = {
            "day": "Hoje",
            "week": "Semana atual",
            "month": "Mês atual",
            "total": "Total",
        }
        contagem = {}
        for n in notes:
            if not n.get("conferido", False) or not in_period(n):
                continue
            nome = n.get("conferido_por") or n.get("conferente_name") or "Desconhecido"
            contagem[nome] = contagem.get(nome, 0) + 1

        period_labels_clean = {
            "day": "Hoje",
            "week": "Semana atual",
            "month": "M\u00eas atual",
            "total": "Total",
        }
        periodo_label = period_labels_clean.get(period, "M\u00eas atual")
        rows = sorted(contagem.items(), key=lambda item: (-item[1], item[0]))[:4]

        if hasattr(self, "conference_table"):
            table = self.conference_table
            table.setRowCount(0)
            table.setHorizontalHeaderLabels([periodo_label, "Notas"])
            if rows:
                for nome, qtd in rows:
                    row = table.rowCount()
                    table.insertRow(row)
                    name_item = QtWidgets.QTableWidgetItem(str(nome))
                    count_item = QtWidgets.QTableWidgetItem(str(qtd))
                    name_item.setTextAlignment(QtCore.Qt.AlignCenter)
                    count_item.setTextAlignment(QtCore.Qt.AlignCenter)
                    table.setItem(row, 0, name_item)
                    table.setItem(row, 1, count_item)
            else:
                table.insertRow(0)
                empty_item = QtWidgets.QTableWidgetItem("Sem conferencia")
                count_item = QtWidgets.QTableWidgetItem("0")
                empty_item.setTextAlignment(QtCore.Qt.AlignCenter)
                count_item.setTextAlignment(QtCore.Qt.AlignCenter)
                table.setItem(0, 0, empty_item)
                table.setItem(0, 1, count_item)
            table.resizeRowsToContents()
        elif hasattr(self, "label_contador"):
            if rows:
                linhas = [f"{nome}: {qtd} nota{'s' if qtd != 1 else ''}" for nome, qtd in rows]
                texto = f"{periodo_label}\n" + "\n".join(linhas)
            else:
                texto = f"{periodo_label}\nNenhuma conferencia."
            self.label_contador.setText(texto)
        return

        periodo_label = period_labels.get(period, "Mês atual")
        if contagem:
            linhas = [
                f"{nome}: {qtd} nota{'s' if qtd != 1 else ''}"
                for nome, qtd in sorted(contagem.items(), key=lambda item: (-item[1], item[0]))[:4]
            ]
            texto = f"{periodo_label}\n" + "\n".join(linhas)
        else:
            texto = f"{periodo_label}\nNenhuma conferência."

        if hasattr(self, "label_contador"):
            self.label_contador.setText(texto)
        return

        conferidas = [n for n in notes if n.get("conferido", False)]
        contagem = {}
        for n in conferidas:
            nome = n.get("conferido_por") or n.get("conferente_name") or "Desconhecido"
            contagem[nome] = contagem.get(nome, 0) + 1

        if not contagem:
            texto = "Nenhuma nota conferida dentro do filtro atual."
        else:
            linhas = [f"{nome}: {qtd} notas" for nome, qtd in sorted(contagem.items())]
            texto = "Ritmo por conferente\n" + "\n".join(linhas)

        if hasattr(self, "label_contador"):
            self.label_contador.setText(texto)

    def _on_table_context_menu(self, pos):
        utils.diagnostic_log("context_menu_requested", pos_x=pos.x(), pos_y=pos.y())
        index = self.table.indexAt(pos)
        if not index.isValid():
            utils.diagnostic_log("context_menu_invalid_index")
            return
        row = index.row()
        col = index.column()
        self.table.selectRow(row)
        note = self._get_note_by_row(row)
        is_locked = bool(note and note.get("conferido", False))
        utils.diagnostic_log(
            "context_menu_note_selected",
            row=row,
            col=col,
            note_id=(note or {}).get("id"),
            nf_number=(note or {}).get("nf_number"),
            is_locked=is_locked,
        )

        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Acoes da nota")
        dialog.setModal(True)
        dialog.setFixedSize(310, 280 if col == 4 else 230)
        dialog._pending_action = None

        layout = QtWidgets.QVBoxLayout(dialog)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        title = make_label(dialog, f"Nota {note.get('nf_number') if note else ''}", hero=True, anchor="center")
        layout.addWidget(title, 0, QtCore.Qt.AlignCenter)

        def add_action_button(text, handler, enabled=True, accent=False):
            button = QtWidgets.QPushButton(text, dialog)
            button.setEnabled(enabled)
            style_button(button, accent=accent, quiet=not accent)
            layout.addWidget(button)

            def choose_action():
                utils.diagnostic_log("context_menu_action_chosen", text=text, row=row)
                dialog._pending_action = handler
                dialog.accept()

            button.clicked.connect(choose_action)
            return button

        if col == 4:
            add_action_button("Alterar CNPJ", lambda r=row: self._edit_cnpj_for_row(r), enabled=not is_locked)
        add_action_button("Material Conferido", lambda r=row: self._mark_conferido(r), accent=True)
        add_action_button("Editar linha", lambda r=row: self._edit_line(r), enabled=not is_locked)
        add_action_button("Excluir nota", lambda r=row: self._remove_line(r))

        close_button = QtWidgets.QPushButton("Fechar", dialog)
        style_button(close_button, quiet=True)
        close_button.clicked.connect(dialog.reject)
        layout.addWidget(close_button)

        utils.diagnostic_log("context_menu_action_dialog_exec_start", row=row, col=col)
        self._exec_modal_dialog(dialog, y_offset=12)
        utils.diagnostic_log("context_menu_action_dialog_exec_done", row=row, col=col)
        pending_action = getattr(dialog, "_pending_action", None)
        if pending_action:
            utils.diagnostic_log("context_menu_pending_action_start", row=row, col=col)
            pending_action()
            utils.diagnostic_log("context_menu_pending_action_done", row=row, col=col)

    def _on_table_double_click(self, row, col):
        if col == 4:
            self._edit_cnpj_for_row(row)
            return
        self._edit_line(row)

    def _remove_line(self, row):
        n = self._get_note_by_row(row)
        if not n:
            return
        msg = QtWidgets.QMessageBox(self)
        msg.setWindowTitle("Excluir nota")
        msg.setText(f"Excluir completamente a nota {n.get('nf_number')}?")
        msg.setIcon(QtWidgets.QMessageBox.Question)
        btn_yes = msg.addButton("Sim", QtWidgets.QMessageBox.YesRole)
        msg.addButton("N\u00e3o", QtWidgets.QMessageBox.NoRole)
        msg.setDefaultButton(btn_yes)
        msg.exec()
        if msg.clickedButton() is not btn_yes:
            return
        notes = utils.load_notes()
        new_notes = [x for x in notes if str(x.get("nf_number")) != str(n.get("nf_number"))]
        ok = self._save_notes_list(new_notes)
        if not ok:
            QtWidgets.QMessageBox.warning(self, "Aviso", "Nao foi possivel salvar automaticamente. Atualize utils_estoque.")
        self.refresh_table()
        QtWidgets.QMessageBox.information(self, "Sucesso", "Nota removida.")

    def _mark_conferido(self, row):
        utils.diagnostic_log("mark_conferido_start", row=row)
        n = self._get_note_by_row(row)
        if not n:
            utils.diagnostic_log("mark_conferido_no_note", row=row)
            return
        utils.diagnostic_log(
            "mark_conferido_note_loaded",
            row=row,
            note_id=n.get("id"),
            nf_number=n.get("nf_number"),
            already_conferido=bool(n.get("conferido", False)),
        )

        if n.get("conferido", False):
            utils.diagnostic_log("mark_conferido_unmark_question_start", note_id=n.get("id"))
            resp = QtWidgets.QMessageBox.question(
                self,
                "Desmarcar",
                f"A nota {n['nf_number']} ja esta conferida.\nDeseja desmarcar?",
            )
            utils.diagnostic_log("mark_conferido_unmark_question_done", response=str(resp))
            if resp == QtWidgets.QMessageBox.Yes:
                try:
                    utils.diagnostic_log("mark_conferido_unmark_update_start", note_id=n.get("id"))
                    if self._update_note_fields(n, {"conferido": False, "conferido_por": None, "conferido_em": None}):
                        utils.diagnostic_log("mark_conferido_unmark_update_done", note_id=n.get("id"))
                        QtWidgets.QMessageBox.information(self, "Sucesso", "Nota desmarcada como conferida.")
                        utils.diagnostic_log("mark_conferido_unmark_refresh_start", note_id=n.get("id"))
                        self.refresh_table()
                        utils.diagnostic_log("mark_conferido_unmark_refresh_done", note_id=n.get("id"))
                    else:
                        utils.diagnostic_log("mark_conferido_unmark_update_false", note_id=n.get("id"))
                        QtWidgets.QMessageBox.warning(self, "Aviso", "Nao foi possivel desmarcar a nota.")
                except Exception as exc:
                    utils.log_exception("Falha ao desmarcar nota como conferida", exc)
                    QtWidgets.QMessageBox.critical(
                        self,
                        "Erro ao desmarcar",
                        "Nao foi possivel desmarcar a nota. "
                        f"O detalhe foi salvo em:\n{utils.runtime_log_path()}",
                    )
            return

        utils.diagnostic_log("mark_conferido_dialog_build_start", note_id=n.get("id"))
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Marcar como conferido")
        dialog.setModal(True)
        dialog.setFixedSize(360, 250)
        layout = QtWidgets.QVBoxLayout(dialog)

        layout.addWidget(make_label(dialog, f"Nota: {n.get('nf_number')}"))
        conf_list = self._conferente_names()
        conf_var = CenteredComboBox(dialog)
        conf_var.addItems(conf_list)
        style_combo_field(conf_var, center=True)
        if n.get("conferido_por"):
            idx = conf_var.findText(n.get("conferido_por"))
            if idx >= 0:
                conf_var.setCurrentIndex(idx)
        layout.addWidget(conf_var)

        layout.addWidget(make_label(dialog, "Data de conferencia:"))
        date_entry = QtWidgets.QLineEdit(dialog)
        date_entry.setText(datetime.now().strftime("%d-%m-%Y"))
        style_text_field(date_entry, center=True)
        layout.addWidget(date_entry)

        btns = QtWidgets.QHBoxLayout()
        btn_confirm = QtWidgets.QPushButton("Confirmar", dialog)
        style_button(btn_confirm, accent=True)
        btn_cancel = QtWidgets.QPushButton("Cancelar", dialog)
        style_button(btn_cancel, quiet=True)
        btns.addWidget(btn_confirm)
        btns.addWidget(btn_cancel)
        layout.addLayout(btns)

        def do_mark():
            utils.diagnostic_log("mark_conferido_confirm_clicked", note_id=n.get("id"))
            chosen = conf_var.currentText()
            d = date_entry.text().strip()
            utils.diagnostic_log(
                "mark_conferido_confirm_values",
                note_id=n.get("id"),
                conferente=chosen,
                data=d,
            )
            if not chosen:
                utils.diagnostic_log("mark_conferido_missing_conferente", note_id=n.get("id"))
                QtWidgets.QMessageBox.warning(self, "Aviso", "Selecione um conferente.")
                return

            try:
                datetime.strptime(d, "%d-%m-%Y")
            except Exception:
                utils.diagnostic_log("mark_conferido_invalid_date", note_id=n.get("id"), data=d)
                QtWidgets.QMessageBox.warning(self, "Aviso", "Data invalida. Use DD-MM-YYYY.")
                return

            try:
                utils.diagnostic_log("mark_conferido_update_start", note_id=n.get("id"))
                updated = self._update_note_fields(
                    n,
                    {
                        "conferido": True,
                        "conferido_por": chosen,
                        "conferido_em": d,
                    },
                )
                utils.diagnostic_log("mark_conferido_update_done", note_id=n.get("id"), updated=updated)
                if not updated:
                    QtWidgets.QMessageBox.warning(self, "Aviso", "Nao foi possivel marcar a nota como conferida.")
                    return

                utils.diagnostic_log("mark_conferido_refresh_start", note_id=n.get("id"))
                self.refresh_table()
                utils.diagnostic_log("mark_conferido_refresh_done", note_id=n.get("id"))
                utils.diagnostic_log("mark_conferido_dialog_accept_start", note_id=n.get("id"))
                dialog.accept()
                utils.diagnostic_log("mark_conferido_dialog_accept_done", note_id=n.get("id"))
                utils.diagnostic_log("mark_conferido_success_message_start", note_id=n.get("id"))
                QtWidgets.QMessageBox.information(self, "Sucesso", "Marcado como conferido.")
                utils.diagnostic_log("mark_conferido_success_message_done", note_id=n.get("id"))
                utils.diagnostic_log("mark_conferido_toast_start", note_id=n.get("id"))
                Toast(self, f"Nota {n.get('nf_number')} conferida!")
                utils.diagnostic_log("mark_conferido_toast_done", note_id=n.get("id"))
            except Exception as exc:
                utils.log_exception("Falha ao marcar nota como conferida", exc)
                QtWidgets.QMessageBox.critical(
                    self,
                    "Erro ao marcar",
                    "Nao foi possivel marcar a nota como conferida. "
                    f"O detalhe foi salvo em:\n{utils.runtime_log_path()}",
                )

        btn_confirm.clicked.connect(do_mark)
        btn_cancel.clicked.connect(dialog.reject)
        utils.diagnostic_log("mark_conferido_dialog_exec_start", note_id=n.get("id"))
        self._exec_modal_dialog(dialog)
        utils.diagnostic_log("mark_conferido_dialog_exec_done", note_id=n.get("id"))

    def _make_cnpj_combo(self, parent, current_value=None):
        combo = CenteredComboBox(parent)
        for label, value in self.CNPJ_OPTIONS:
            combo.addItem(label, value)
        combo.setFixedWidth(242)
        combo.setProperty("minimumTextPointSize", 8)
        font = combo.font()
        font.setPointSize(9)
        combo.setFont(font)
        style_combo_field(combo, center=True)

        current_text = str(current_value or "").strip()
        for index in range(combo.count()):
            if current_text in (str(combo.itemData(index)), combo.itemText(index)):
                combo.setCurrentIndex(index)
                break
        return combo

    def _selected_cnpj(self, combo):
        return str(combo.currentData() or combo.currentText()).strip()

    def _date_from_note_text(self, text):
        for fmt in ("%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y"):
            try:
                return QtCore.QDate.fromString(datetime.strptime(str(text), fmt).strftime("%d-%m-%Y"), "dd-MM-yyyy")
            except Exception:
                continue
        return QtCore.QDate.currentDate()

    def _update_note_fields(self, note, fields):
        note_id = note.get("id")
        if note_id:
            updated_notes = utils.update_note(note_id, fields)
            note.update(fields)
            updated_note = next(
                (item for item in updated_notes if str(item.get("id")) == str(note_id)),
                note,
            )
            utils.acknowledge_note_change(updated_note)
            return True

        notes = utils.load_notes()
        edited = False
        for item in notes:
            if str(item.get("nf_number")) == str(note.get("nf_number")):
                item.update(fields)
                edited = True
                break
        if not edited:
            return False
        saved = self._save_notes_list(notes)
        if saved:
            note.update(fields)
            utils.acknowledge_note_change(note)
        return saved

    def _warn_note_locked(self):
        QtWidgets.QMessageBox.warning(
            self,
            "Nota conferida",
            "Essa nota j\u00e1 foi conferida.",
        )

    def _edit_cnpj_for_row(self, row):
        n = self._get_note_by_row(row)
        if not n:
            return
        if n.get("conferido", False):
            self._warn_note_locked()
            return

        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Alterar CNPJ")
        dialog.setModal(True)
        dialog.setFixedSize(360, 190)
        layout = QtWidgets.QVBoxLayout(dialog)
        layout.setSpacing(10)

        title = make_label(dialog, f"Nota {n.get('nf_number')}", hero=True, anchor="center")
        layout.addWidget(title, 0, QtCore.Qt.AlignCenter)
        label = make_label(dialog, "CNPJ:", muted=True, anchor="center")
        label.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(label, 0, QtCore.Qt.AlignCenter)

        cnpj_combo = self._make_cnpj_combo(dialog, n.get("cnpj"))
        layout.addWidget(cnpj_combo, 0, QtCore.Qt.AlignCenter)

        btns = QtWidgets.QHBoxLayout()
        btns.setContentsMargins(0, 0, 0, 0)
        btns.setSpacing(8)
        btn_save = QtWidgets.QPushButton("Salvar", dialog)
        style_button(btn_save, accent=True)
        btn_cancel = QtWidgets.QPushButton("Cancelar", dialog)
        style_button(btn_cancel, quiet=True)
        btns.addWidget(btn_save)
        btns.addWidget(btn_cancel)
        layout.addLayout(btns)

        def do_save_cnpj():
            if self._update_note_fields(n, {"cnpj": self._selected_cnpj(cnpj_combo)}):
                self.refresh_table()
                dialog.accept()
                QtWidgets.QMessageBox.information(self, "Sucesso", "CNPJ atualizado.")
            else:
                QtWidgets.QMessageBox.warning(self, "Aviso", "Nao foi possivel atualizar o CNPJ.")

        btn_save.clicked.connect(do_save_cnpj)
        btn_cancel.clicked.connect(dialog.reject)
        self._exec_modal_dialog(dialog)

    def _edit_line(self, row):
        n = self._get_note_by_row(row)
        if not n:
            return
        if n.get("conferido", False):
            self._warn_note_locked()
            return
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Editar Nota")
        dialog.setModal(True)
        dialog.setFixedSize(420, 560)
        layout = QtWidgets.QVBoxLayout(dialog)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(8)

        title = make_label(dialog, "Editar Nota", hero=True, anchor="center")
        layout.addWidget(title, 0, QtCore.Qt.AlignCenter)

        label_count = {"value": 0}

        def add_field_label(text):
            if label_count["value"]:
                layout.addSpacing(6)
            label = make_label(dialog, text, muted=True, anchor="center")
            label.setAlignment(QtCore.Qt.AlignCenter)
            layout.addWidget(label, 0, QtCore.Qt.AlignCenter)
            label_count["value"] += 1

        add_field_label("No NF:")
        nf_entry = QtWidgets.QLineEdit(dialog)
        nf_entry.setText(str(n.get("nf_number")))
        style_text_field(nf_entry, center=True, width=220)
        layout.addWidget(nf_entry, 0, QtCore.Qt.AlignCenter)

        add_field_label("Data de Chegada:")
        date_entry = ClickableDateEdit(dialog)
        style_date_field(date_entry, width=220, display_format="dd/MM/yyyy")
        date_entry.setDate(self._date_from_note_text(n.get("data_chegada") or utils.today_br()))
        date_entry._sync_display_text()
        layout.addWidget(date_entry, 0, QtCore.Qt.AlignCenter)

        add_field_label("Data de Emissao:")
        date_emissao_entry = ClickableDateEdit(dialog)
        style_date_field(date_emissao_entry, width=220, display_format="dd/MM/yyyy")
        date_emissao_entry.setDate(self._date_from_note_text(n.get("data_emissao") or utils.today_br()))
        date_emissao_entry._sync_display_text()
        layout.addWidget(date_emissao_entry, 0, QtCore.Qt.AlignCenter)

        add_field_label("CNPJ:")
        cnpj_combo = self._make_cnpj_combo(dialog, n.get("cnpj"))
        layout.addWidget(cnpj_combo, 0, QtCore.Qt.AlignCenter)

        add_field_label("Fornecedor:")
        sup_combo = QtWidgets.QComboBox(dialog)
        sup_combo.addItems(self._supplier_names())
        style_combo_field(sup_combo, center=True)
        sup_combo.setFixedWidth(242)
        sup_idx = sup_combo.findText(n.get("fornecedor_name"))
        if sup_idx >= 0:
            sup_combo.setCurrentIndex(sup_idx)
        layout.addWidget(sup_combo, 0, QtCore.Qt.AlignCenter)

        add_field_label("Conferente:")
        conf_combo = QtWidgets.QComboBox(dialog)
        conf_combo.addItems(self._conferente_names())
        style_combo_field(conf_combo, center=True)
        conf_combo.setFixedWidth(242)
        conf_idx = conf_combo.findText(n.get("conferente_name"))
        if conf_idx >= 0:
            conf_combo.setCurrentIndex(conf_idx)
        layout.addWidget(conf_combo, 0, QtCore.Qt.AlignCenter)

        layout.addSpacing(10)
        btns = QtWidgets.QHBoxLayout()
        btns.addStretch(1)
        btn_save = QtWidgets.QPushButton("Salvar", dialog)
        btn_save.setFixedWidth(120)
        style_button(btn_save, accent=True)
        btn_cancel = QtWidgets.QPushButton("Cancelar", dialog)
        btn_cancel.setFixedWidth(120)
        style_button(btn_cancel, quiet=True)
        btns.addWidget(btn_save)
        btns.addWidget(btn_cancel)
        btns.addStretch(1)
        layout.addLayout(btns)

        def do_save_edit():
            nf_new = nf_entry.text().strip()
            d = date_entry.date().toString("dd-MM-yyyy")

            notes = utils.load_notes()
            edited = False

            conferentes = utils.load_conferentes()
            fornecedores = utils.load_suppliers()

            conf_name = conf_combo.currentText()
            forn_name = sup_combo.currentText()

            conf = next((c for c in conferentes if c["name"] == conf_name), None)
            forn = next((f for f in fornecedores if f["name"] == forn_name), None)

            for item in notes:
                if str(item.get("nf_number")) == str(n.get("nf_number")):
                    item["nf_number"] = nf_new
                    item["data_chegada"] = d
                    item["data_emissao"] = date_emissao_entry.date().toString("dd-MM-yyyy")
                    item["cnpj"] = self._selected_cnpj(cnpj_combo)
                    item["fornecedor_name"] = forn_name
                    item["conferente_name"] = conf_name
                    item["recebido_por"] = conf_name
                    if forn:
                        item["fornecedor_id"] = forn["id"]
                    if conf:
                        item["conferente_id"] = conf["id"]
                    edited = True
                    break

            if edited:
                ok = self._save_notes_list(notes)
                if not ok:
                    QtWidgets.QMessageBox.warning(self, "Aviso", "Nao foi possivel salvar automaticamente. Atualize utils_estoque.")
                self.refresh_table()
                dialog.accept()
                QtWidgets.QMessageBox.information(self, "Sucesso", "Nota atualizada.")
            else:
                QtWidgets.QMessageBox.critical(self, "Erro", "Nota nao encontrada.")

        btn_save.clicked.connect(do_save_edit)
        btn_cancel.clicked.connect(dialog.reject)
        self._exec_modal_dialog(dialog)

    def _get_note_by_row(self, row):
        item = self.table.item(row, 0)
        if not item:
            return None
        nf = item.text()
        notes = utils.load_notes()
        for n in notes:
            if str(n.get("nf_number")) == str(nf):
                return n
        return None

    @staticmethod
    def _format_display_date(raw_value):
        if not raw_value:
            return ""

        text = str(raw_value)[:10]
        for fmt in ("%Y-%m-%d", "%d-%m-%Y"):
            try:
                return datetime.strptime(text, fmt).strftime("%d-%m-%Y")
            except Exception:
                continue
        return text
