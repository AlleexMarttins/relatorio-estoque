# utils_estoque.py
import os
import sys
import json
import traceback
import pathlib
import faulthandler
from datetime import datetime
from supabase import create_client
import uuid

def get_mac_address():
    mac = uuid.getnode()
    return ':'.join(("%012X" % mac)[i:i+2] for i in range(0, 12, 2)).lower()

def get_or_create_user(supabase, mac_address):
    """
    So verifica se ja existe no Supabase.
    Se nao existir, retorna None - a UI (tk_estoque) abre a janela para pedir o nome.
    """
    resp = supabase.table("users").select("*").eq("mac", mac_address).execute()
    if resp.data:
        return resp.data[0]
    return None

# ---------------- Fornecedores ----------------
def load_suppliers():
    resp = supabase.table("suppliers").select("*").order("name").execute()  # Ordenando por nome
    return resp.data or []

def add_supplier(name):
    existing = supabase.table("suppliers").select("*").eq("name", name).execute()
    if existing.data:
        return load_suppliers()
    supabase.table("suppliers").insert({"name": name}).execute()
    return load_suppliers()

def remove_supplier(supplier_id):
    """Remove fornecedor, mas impede exclusao se houver notas vinculadas."""

    url = SUPABASE_URL
    key = SUPABASE_KEY
    sb = create_client(url, key)

    # Verifica se ha notas associadas
    related = sb.table("notes").select("id, nf_number, fornecedor_id").eq("fornecedor_id", supplier_id).execute()

    print("DEBUG - supplier_id:", supplier_id)
    print("DEBUG - notas vinculadas:", related.data)

    if related.data:
        return {"error": "linked_notes", "notes": related.data}

    sb.table("suppliers").delete().eq("id", supplier_id).execute()
    return {"success": True}

# ---------------- Conferentes ----------------
def load_conferentes():
    resp = supabase.table("conferentes").select("*").order("name").execute()  # Ordenando por nome
    return resp.data or []

def add_conferente(name):
    existing = supabase.table("conferentes").select("*").eq("name", name).execute()
    if existing.data:
        return load_conferentes()
    supabase.table("conferentes").insert({"name": name}).execute()
    return load_conferentes()

def remove_conferente(conferente_id):
    # Verifica notas relacionadas
    related = supabase.table("notes").select("id, nf_number").eq("conferente_id", conferente_id).execute()

    if related.data:
        return {"error": "linked_notes", "notes": related.data}

    # Se nao tiver vinculos, pode apagar
    supabase.table("conferentes").delete().eq("id", conferente_id).execute()
    return {"success": True}

# ---------------- Notas ----------------
def load_notes():
    resp = supabase.table("notes").select("*").order("created_at").execute()
    return resp.data or []

def save_note(note: dict):
    supabase.table("notes").insert(note).execute()
    return load_notes()

def update_note(note_id, fields: dict):
    diagnostic_log(
        "supabase_update_note_start",
        note_id=note_id,
        fields=list((fields or {}).keys()),
    )
    supabase.table("notes").update(fields).eq("id", note_id).execute()
    diagnostic_log("supabase_update_note_done", note_id=note_id)
    return load_notes()

def remove_note(note_id):
    supabase.table("notes").delete().eq("id", note_id).execute()
    return load_notes()

def save_all_notes(notes: list[dict]):
    current_notes = load_notes()
    current_by_id = {n["id"]: n for n in current_notes if n.get("id")}
    incoming_by_id = {n["id"]: n for n in notes if n.get("id")}

    for note_id in current_by_id.keys() - incoming_by_id.keys():
        supabase.table("notes").delete().eq("id", note_id).execute()

    for note in notes:
        payload = dict(note)
        note_id = payload.pop("id", None)
        if note_id and note_id in current_by_id:
            supabase.table("notes").update(payload).eq("id", note_id).execute()
        else:
            supabase.table("notes").insert(note).execute()

    return load_notes()

# ---------------- Helpers ----------------
def today_br():
    return datetime.now().strftime("%d-%m-%Y")

def app_data_dir():
    appdata = os.getenv("APPDATA") or os.path.expanduser("~")
    cfg_dir = os.path.join(appdata, "RelatorioEstoque")
    os.makedirs(cfg_dir, exist_ok=True)
    return cfg_dir

def runtime_log_path():
    return os.path.join(app_data_dir(), "app.log")

def diagnostic_log_dirs():
    dirs = [app_data_dir()]
    env_dir = os.getenv("ESTOQUE_DIAGNOSTIC_LOG_DIR")
    if env_dir:
        dirs.append(env_dir)
    return list(dict.fromkeys(dirs))

def _diagnostic_log_filename(prefix="diagnostic"):
    computer = os.getenv("COMPUTERNAME") or "unknown-pc"
    user = os.getenv("USERNAME") or "unknown-user"
    safe_name = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in f"{computer}-{user}")
    return f"{prefix}-{safe_name}.log"

def diagnostic_log_paths(prefix="diagnostic"):
    return [os.path.join(path, _diagnostic_log_filename(prefix)) for path in diagnostic_log_dirs()]

def _app_version():
    try:
        from versionfile_generator import APP_VERSION

        return APP_VERSION
    except Exception:
        return "unknown"

def diagnostic_log(event, **details):
    record = {
        "ts": datetime.now().isoformat(timespec="milliseconds"),
        "event": str(event),
        "pid": os.getpid(),
        "computer": os.getenv("COMPUTERNAME"),
        "user": os.getenv("USERNAME"),
        "frozen": bool(getattr(sys, "frozen", False)),
        "exe": os.path.basename(sys.executable or ""),
        "version": _app_version(),
        "details": details,
    }
    line = json.dumps(record, ensure_ascii=False, default=str)

    for path in diagnostic_log_paths():
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "a", encoding="utf-8") as file:
                file.write(line + "\n")
                file.flush()
        except Exception:
            continue

def install_fault_handler():
    if getattr(sys, "_estoque_fault_handler_installed", False):
        return

    for path in diagnostic_log_paths("fatal"):
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            handle = open(path, "a", encoding="utf-8")
            handle.write(f"\n=== fault handler enabled {datetime.now().isoformat()} pid={os.getpid()} ===\n")
            handle.flush()
            faulthandler.enable(file=handle, all_threads=True)
            sys._estoque_fault_log_handle = handle
            sys._estoque_fault_handler_installed = True
            diagnostic_log("fault_handler_enabled", path=path)
            return
        except Exception:
            continue

def log_exception(context, exc=None, exc_info=None):
    if exc_info is None:
        exc_info = sys.exc_info()

    lines = [
        "",
        "=" * 80,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        str(context),
    ]

    if exc_info and exc_info[0]:
        lines.extend(traceback.format_exception(*exc_info))
    elif exc is not None:
        lines.append(repr(exc))

    with open(runtime_log_path(), "a", encoding="utf-8") as file:
        file.write("\n".join(lines).rstrip() + "\n")
    diagnostic_log("exception", context=context, error=repr(exc), has_traceback=bool(exc_info and exc_info[0]))

def install_global_exception_hook():
    if getattr(sys, "_estoque_exception_hook_installed", False):
        return
    install_fault_handler()
    diagnostic_log("exception_hook_install")

    def show_error_message():
        try:
            from PySide6 import QtWidgets

            app = QtWidgets.QApplication.instance()
            parent = app.activeWindow() if app else None
            QtWidgets.QMessageBox.critical(
                parent,
                "Erro inesperado",
                "O aplicativo encontrou um erro inesperado. "
                f"O detalhe foi salvo em:\n{runtime_log_path()}",
            )
        except Exception:
            pass

    def handle_exception(exc_type, exc_value, exc_tb):
        log_exception("Unhandled exception", exc_value, (exc_type, exc_value, exc_tb))
        try:
            from PySide6 import QtCore, QtWidgets

            if QtWidgets.QApplication.instance():
                QtCore.QTimer.singleShot(0, show_error_message)
        except Exception:
            pass

    sys.excepthook = handle_exception

    try:
        import threading

        def handle_thread_exception(args):
            log_exception(
                f"Unhandled thread exception: {getattr(args.thread, 'name', 'thread')}",
                args.exc_value,
                (args.exc_type, args.exc_value, args.exc_traceback),
            )

        threading.excepthook = handle_thread_exception
    except Exception:
        pass

    sys._estoque_exception_hook_installed = True

def resource_path(relative_path: str):
    """Garante que os assets funcionem no PyInstaller"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

_notification_state = {"first_run": True, "signatures": {}}


def _note_signature(note):
    return (
        str(note.get("id") or ""),
        str(note.get("nf_number") or ""),
        str(note.get("fornecedor_name") or ""),
        str(note.get("cnpj") or ""),
        str(note.get("recebido_por") or note.get("conferente_name") or ""),
        str(note.get("data_chegada") or ""),
        bool(note.get("conferido", False)),
        str(note.get("conferido_por") or ""),
        str(note.get("conferido_em") or ""),
    )


def acknowledge_note_change(note):
    """Prevent the polling loop from repeating feedback for a local change."""
    note_id = str((note or {}).get("id") or "")
    if note_id:
        _notification_state["signatures"][note_id] = _note_signature(note)


def poll_notifications(app):
    """Verifica mudancas nas notas e atualiza a UI apenas quando necessario."""
    from PySide6 import QtCore
    from system.ui_components import Toast

    def check():
        try:
            notes = load_notes()
            current = {str(n.get("id")): _note_signature(n) for n in notes if n.get("id")}
            previous = _notification_state["signatures"]

            if _notification_state["first_run"]:
                _notification_state["signatures"] = current
                _notification_state["first_run"] = False
                return

            added = current.keys() - previous.keys()
            removed = previous.keys() - current.keys()
            changed = {
                note_id for note_id in current.keys() & previous.keys()
                if current[note_id] != previous[note_id]
            }

            for n in notes:
                note_id = str(n.get("id"))
                if note_id in added:
                    if n.get("conferido", False):
                        diagnostic_log("poll_notification_toast_start", note_id=note_id, kind="added_conferido")
                        Toast(app, f"Nota {n['nf_number']} conferida!")
                        diagnostic_log("poll_notification_toast_done", note_id=note_id, kind="added_conferido")
                    else:
                        diagnostic_log("poll_notification_toast_start", note_id=note_id, kind="added")
                        Toast(app, f"Nota {n['nf_number']} adicionada!")
                        diagnostic_log("poll_notification_toast_done", note_id=note_id, kind="added")
                elif note_id in changed:
                    previous_sig = previous.get(note_id, ())
                    was_conferido = bool(previous_sig[6]) if len(previous_sig) > 6 else False
                    if not was_conferido and n.get("conferido", False):
                        diagnostic_log("poll_notification_toast_start", note_id=note_id, kind="changed_conferido")
                        Toast(app, f"Nota {n['nf_number']} conferida!")
                        diagnostic_log("poll_notification_toast_done", note_id=note_id, kind="changed_conferido")

            if (added or removed or changed) and hasattr(app, "refresh_table"):
                diagnostic_log(
                    "poll_notification_refresh",
                    added=len(added),
                    removed=len(removed),
                    changed=len(changed),
                )
                app.refresh_table()

            _notification_state["signatures"] = current

        except Exception as e:
            diagnostic_log("poll_notifications_error", error=repr(e))
            print("Erro ao checar notificacoes:", e)

    timer = QtCore.QTimer(app)
    timer.setInterval(5000)
    timer.timeout.connect(check)
    timer.start()
    app._notification_timer = timer
    check()

config_path = resource_path(os.path.join("data", "credentials.json"))

with open(config_path, "r", encoding="utf-8") as f:
    config = json.load(f)

SUPABASE_URL = config.get("SUPABASE_URL")
SUPABASE_KEY = config.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ---------------- Settings ----------------

def settings_path():
    return os.path.join(app_data_dir(), "settings.json")

def load_settings():
    path = settings_path()
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"visualizar_todos_meses": False}  # default

def save_settings(settings: dict):
    with open(settings_path(), "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)

# ---------------- Update Checker ----------------

def check_for_updates(root):
    import requests
    import threading
    import zipfile
    import shutil
    import subprocess
    import re
    from PySide6 import QtCore, QtWidgets
    from versionfile_generator import APP_VERSION

    GITHUB_REPO = "AlleexMarttins/relatorio-estoque"
    APP_DIR_NAME = "RelatorioEstoque"
    APP_EXE_NAMES = (
        "Relatorio de Estoque.exe",
        "Relatorio do Estoque.exe",
        "RelatorioEstoque.exe",
    )

    class UiInvoker(QtCore.QObject):
        run = QtCore.Signal(object)

    invoker = UiInvoker(root)
    invoker.run.connect(lambda callback: callback())
    root._update_invoker = invoker

    def run_on_ui(callback):
        try:
            invoker.run.emit(callback)
        except RuntimeError:
            pass

    def version_key(raw: str):
        text = (raw or "").strip().lstrip("vV")
        nums = [int(part) for part in re.findall(r"\d+", text)]
        while len(nums) < 4:
            nums.append(0)
        return tuple(nums[:4])

    def resolve_latest_release():
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "RelatorioEstoque-Updater",
        }
        timeout = 20

        try:
            response = requests.get(
                f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest",
                headers=headers,
                timeout=timeout,
            )
            response.raise_for_status()
            data = response.json()
            if data and data.get("tag_name"):
                return data
        except Exception:
            pass

        try:
            response = requests.get(
                f"https://api.github.com/repos/{GITHUB_REPO}/releases",
                headers=headers,
                timeout=timeout,
            )
            response.raise_for_status()
            releases = response.json() or []
            candidates = [
                release
                for release in releases
                if not release.get("draft")
                and not release.get("prerelease")
                and release.get("tag_name")
            ]
            if not candidates:
                return None
            candidates.sort(key=lambda release: version_key(release.get("tag_name", "")), reverse=True)
            return candidates[0]
        except Exception:
            return None

    def choose_release_asset(assets):
        if not assets:
            return None

        for suffix in (".zip", ".exe"):
            for asset in assets:
                name = str(asset.get("name", "")).lower()
                if name.endswith(suffix) and asset.get("browser_download_url"):
                    return asset
        return None

    def app_update_dir(version):
        base_dir = os.path.join(os.getenv("LOCALAPPDATA", "."), APP_DIR_NAME)
        target_dir = os.path.join(base_dir, f"app-{version}")
        os.makedirs(target_dir, exist_ok=True)
        return base_dir, target_dir

    def install_marker_path(base_dir):
        return os.path.join(base_dir, "latest.json")

    def current_executable_path():
        return os.path.abspath(sys.executable if getattr(sys, "frozen", False) else sys.argv[0])

    def read_installed_release(base_dir):
        try:
            with open(install_marker_path(base_dir), "r", encoding="utf-8") as file:
                data = json.load(file)
            exe_path = os.path.abspath(data.get("exe_path") or "")
            version = str(data.get("version") or "")
            if version and exe_path and os.path.exists(exe_path):
                return {"version": version, "exe_path": exe_path}
        except Exception:
            return None
        return None

    def write_installed_release(base_dir, version, exe_path):
        data = {
            "version": version,
            "exe_path": os.path.abspath(exe_path),
            "installed_at": datetime.now().isoformat(),
        }
        with open(install_marker_path(base_dir), "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)

    def launch_installed_release_if_newer(latest_version):
        if not getattr(sys, "frozen", False):
            return False

        base_dir = os.path.join(os.getenv("LOCALAPPDATA", "."), APP_DIR_NAME)
        installed = read_installed_release(base_dir)
        if not installed:
            return False

        installed_version = installed["version"]
        installed_exe = installed["exe_path"]
        current_exe = current_executable_path()
        try:
            same_file = pathlib.Path(installed_exe).resolve() == pathlib.Path(current_exe).resolve()
        except Exception:
            same_file = os.path.normcase(installed_exe) == os.path.normcase(current_exe)

        if (
            not same_file
            and version_key(installed_version) >= version_key(latest_version)
            and version_key(installed_version) > version_key(APP_VERSION)
        ):
            subprocess.Popen([installed_exe], cwd=os.path.dirname(installed_exe))
            QtWidgets.QApplication.quit()
            return True

        return False

    def safe_extract_zip(zip_path, extract_dir):
        target_root = os.path.abspath(extract_dir)
        with zipfile.ZipFile(zip_path, "r") as zip_file:
            for member in zip_file.infolist():
                member_path = os.path.abspath(os.path.join(extract_dir, member.filename))
                if not member_path.startswith(target_root + os.sep) and member_path != target_root:
                    raise RuntimeError("Arquivo invalido no pacote de atualizacao.")
            zip_file.extractall(extract_dir)

    def find_executable(extract_dir):
        expected = {name.lower() for name in APP_EXE_NAMES}
        first_exe = None

        for root_dir, _dirs, files in os.walk(extract_dir):
            for filename in files:
                if not filename.lower().endswith(".exe"):
                    continue
                exe_path = os.path.join(root_dir, filename)
                if filename.lower() in expected:
                    return exe_path
                if first_exe is None:
                    first_exe = exe_path

        return first_exe

    def download_asset(asset, latest_version):
        base_dir, extract_dir = app_update_dir(latest_version)
        asset_name = os.path.basename(asset.get("name") or "")
        asset_url = asset["browser_download_url"]
        is_zip = asset_name.lower().endswith(".zip")
        download_path = os.path.join(base_dir, asset_name or f"RelatorioEstoque-{latest_version}.zip")

        response = requests.get(asset_url, stream=True, timeout=60)
        response.raise_for_status()
        with open(download_path, "wb") as file:
            for chunk in response.iter_content(1024 * 256):
                if chunk:
                    file.write(chunk)

        if os.path.exists(extract_dir):
            shutil.rmtree(extract_dir, ignore_errors=True)
        os.makedirs(extract_dir, exist_ok=True)

        if is_zip:
            safe_extract_zip(download_path, extract_dir)
            exe_path = find_executable(extract_dir)
        else:
            exe_name = asset_name if asset_name.lower().endswith(".exe") else APP_EXE_NAMES[0]
            exe_path = os.path.join(extract_dir, exe_name)
            shutil.copy2(download_path, exe_path)

        if not exe_path or not os.path.exists(exe_path):
            raise RuntimeError("Nao foi possivel localizar o executavel na atualizacao.")

        write_installed_release(base_dir, latest_version, exe_path)
        return exe_path

    def worker():
        try:
            data = resolve_latest_release()
            if not data or not data.get("tag_name"):
                return

            latest_version = data["tag_name"].lstrip("vV")

            if version_key(latest_version) > version_key(APP_VERSION):
                if launch_installed_release_if_newer(latest_version):
                    return

                settings = load_settings()
                if settings.get("ignored_update_version") == latest_version:
                    return

                def ask_user():
                    resp = QtWidgets.QMessageBox.question(
                        root,
                        "Atualizacao Disponivel",
                        f"Uma nova versao ({latest_version}) esta disponivel. Deseja baixar e reiniciar agora?",
                    )
                    if resp != QtWidgets.QMessageBox.Yes:
                        settings = load_settings()
                        settings["ignored_update_version"] = latest_version
                        save_settings(settings)
                        return

                    asset = choose_release_asset(data.get("assets", []))
                    if not asset:
                        QtWidgets.QMessageBox.critical(
                            root,
                            "Erro na Atualizacao",
                            "Nenhum arquivo .zip ou .exe foi encontrado na release.",
                        )
                        return

                    try:
                        exe_path = download_asset(asset, latest_version)
                        settings = load_settings()
                        settings.pop("ignored_update_version", None)
                        save_settings(settings)
                        QtWidgets.QMessageBox.information(
                            root,
                            "Atualizado",
                            "Nova versao baixada e instalada. O aplicativo sera reiniciado.",
                        )
                        subprocess.Popen([exe_path], cwd=os.path.dirname(exe_path))
                        QtWidgets.QApplication.quit()
                    except Exception as e:
                        QtWidgets.QMessageBox.critical(root, "Erro no Download", f"Ocorreu um erro: {e}")

                run_on_ui(ask_user)
            else:
                print("App atualizado.")

        except Exception as e:
            if root and root.isVisible():
                run_on_ui(
                    lambda: QtWidgets.QMessageBox.critical(
                        root,
                        "Erro na Atualizacao",
                        f"Ocorreu um erro ao checar atualizacoes: {e}",
                    )
                )

    threading.Thread(target=worker, daemon=True).start()
