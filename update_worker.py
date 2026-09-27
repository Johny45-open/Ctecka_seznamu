"""QThread worker pro kontrolu aktualizací.

Síťová kontrola nesmí běžet v GUI threadu. Worker pouze volá
update_checker.check_for_updates() a výsledek předá signálem
zpět do GUI threadu. Žádná manipulace s GUI objekty zde.
"""

from PyQt6.QtCore import QThread, pyqtSignal

from update_checker import UpdateCheckResult, check_for_updates


class UpdateCheckWorker(QThread):
    """Worker běžící mimo GUI thread. Signál finished je doručen do GUI threadu."""

    finished = pyqtSignal(object)  # UpdateCheckResult

    def __init__(self, current_version=None, parent=None):
        super().__init__(parent)
        self._current_version = current_version

    def run(self):
        try:
            result = check_for_updates(current_version=self._current_version)
        except Exception as e:  # nouzová pojistka, check_for_updates by neměl vyhazovat
            from update_checker import MSG_UNAVAILABLE, UpdateCheckResult
            from version import APP_VERSION

            result = UpdateCheckResult(
                status="error",
                current_version=self._current_version or APP_VERSION,
                error_kind="unavailable",
                error_message=f"{MSG_UNAVAILABLE} ({e})",
            )
        self.finished.emit(result)
