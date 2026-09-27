"""Přístupný dialog kontroly aktualizací (PyQt6, bez vlastního TTS).

Stavy: kontroluji / aktuální / nová verze / chyba.
Veškerá oznámení probíhají nativním dialogem čitelným pro NVDA.
Nepoužívá speaker.speak() ani print().
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QDialogButtonBox,
)
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtCore import QUrl


class UpdateDialog(QDialog):
    """Dialog pro zobrazení výsledku kontroly aktualizací."""

    def __init__(self, current_version: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Kontrola aktualizací")
        self.setModal(True)
        self.setMinimumWidth(420)
        self.setAccessibleName("Dialog kontroly aktualizací")
        self.setAccessibleDescription(
            "Zobrazuje výsledek kontroly aktualizací aplikace Čtečka seznamů."
        )
        self._release_url = None

        self.layout = QVBoxLayout(self)

        self.status_label = QLabel("Kontroluji dostupnost aktualizací…")
        self.status_label.setWordWrap(True)
        self.status_label.setAccessibleName("Stav kontroly aktualizací")
        self.layout.addWidget(self.status_label)

        self.detail_label = QLabel(f"Aktuálně používaná verze: {current_version}")
        self.detail_label.setWordWrap(True)
        self.detail_label.setAccessibleName("Podrobnosti o verzi")
        self.layout.addWidget(self.detail_label)

        # Tlačítka – přestavují se podle stavu (viz _rebuild_buttons)
        self.button_layout = QHBoxLayout()
        self.layout.addLayout(self.button_layout)
        self._buttons = []

        self._close_on_escape = True
        self.set_checking(current_version)

    # -- pomocné --
    def _clear_buttons(self):
        for btn in self._buttons:
            self.button_layout.removeWidget(btn)
            btn.deleteLater()
        self._buttons = []

    def _add_button(self, text, acc_name, acc_desc, role_default=False, connected=None):
        btn = QPushButton(text, self)
        btn.setAccessibleName(acc_name)
        btn.setAccessibleDescription(acc_desc)
        if connected is not None:
            btn.clicked.connect(connected)
        self.button_layout.addWidget(btn)
        self._buttons.append(btn)
        if role_default:
            btn.setDefault(True)
            btn.setFocus()
        return btn

    def _finish_tab_order(self):
        for a, b in zip(self._buttons, self._buttons[1:]):
            self.setTabOrder(a, b)

    # -- stavy --
    def set_checking(self, current_version: str):
        """Stav během síťové kontroly (voláno z GUI threadu před startem workeru)."""
        self._release_url = None
        self.status_label.setText("Kontroluji dostupnost aktualizací…")
        self.status_label.setAccessibleDescription("Kontrola aktualizací právě probíhá.")
        self.detail_label.setText(f"Aktuálně používaná verze: {current_version}")
        self._clear_buttons()
        self.close_btn = self._add_button(
            "Zavřít", "Zavřít",
            "Zavře dialog. Kontrola na pozadí doběhne bez zobrazení výsledku.",
            role_default=False, connected=self.reject,
        )
        self._finish_tab_order()

    def set_result(self, result):
        """Naplní dialog výsledkem UpdateCheckResult. Volat pouze z GUI threadu."""
        self._release_url = getattr(result, "release_url", None)
        self._clear_buttons()

        if result.status == "update_available":
            self.status_label.setText("Byla nalezena nová verze.")
            self.status_label.setAccessibleDescription("Je dostupná nová verze aplikace.")
            self.detail_label.setText(
                f"Aktuálně používaná verze: {result.current_version}\n"
                f"Nejnovější dostupná verze: {result.latest_version}"
            )
            self.detail_label.setAccessibleDescription(
                f"Aktuální verze {result.current_version}, "
                f"nejnovější verze {result.latest_version}."
            )
            self.download_btn = self._add_button(
                "Stáhnout aktualizaci", "Stáhnout aktualizaci",
                "Otevře stránku vydání nové verze v prohlížeči. Instalaci provedete ručně.",
                role_default=True, connected=self._on_download,
            )
            if self._release_url:
                self.info_btn = self._add_button(
                    "Zobrazit informace o vydání", "Zobrazit informace o vydání",
                    "Otevře stránku vydání s popisem změn v prohlížeči.",
                    connected=self._on_download,
                )
            self.later_btn = self._add_button(
                "Později", "Později",
                "Zavře dialog a aktualizaci připomene později.",
                connected=self.reject,
            )
            # Escape = Později (neblokuje aplikaci)
            self._escape_btn = self.later_btn

        elif result.status == "up_to_date":
            self.status_label.setText(
                f"Používáš nejnovější dostupnou verzi {result.latest_version or result.current_version}."
            )
            self.status_label.setAccessibleDescription("Aplikace je aktuální.")
            self.detail_label.setText(f"Aktuálně používaná verze: {result.current_version}")
            self.ok_btn = self._add_button(
                "OK", "OK",
                "Zavře dialog kontroly aktualizací.",
                role_default=True, connected=self.accept,
            )
            self._escape_btn = self.ok_btn

        else:  # error
            reason = getattr(result, "error_message", "") or ""
            self.status_label.setText("Nepodařilo se zkontrolovat aktualizace.")
            self.status_label.setAccessibleDescription(
                "Kontrola aktualizací selhala. " + reason if reason else "Kontrola aktualizací selhala."
            )
            text = "Nepodařilo se zkontrolovat aktualizace."
            if reason:
                text += f"\n{reason}"
            self.detail_label.setText(text)
            self.ok_btn = self._add_button(
                "OK", "OK",
                "Zavře dialog kontroly aktualizací.",
                role_default=True, connected=self.accept,
            )
            self._escape_btn = self.ok_btn

        self._finish_tab_order()
        if self._buttons:
            self._buttons[0].setFocus()

    # -- akce --
    def _on_download(self):
        """Pouze otevře html_url releasu v prohlížeči. Žádné stahování/instalace."""
        if self._release_url:
            QDesktopServices.openUrl(QUrl(self._release_url))
        self.accept()

    def reject(self):
        super().reject()

    def accept(self):
        super().accept()
