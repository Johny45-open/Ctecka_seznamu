from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QComboBox,
    QCheckBox, QSpinBox, QDoubleSpinBox, QPushButton,
    QHBoxLayout, QFormLayout, QGroupBox, QDialogButtonBox
)
from PyQt6.QtCore import Qt


class SettingsDialog(QDialog):
    """Společný dialog pro prvotní nastavení i běžné Nastavení.

    Args:
        current_config: dict s aktuálními hodnotami (nebo výchozími při first_run)
        parent: rodičovský widget
        first_run: True = prvotní spuštění, False = běžné otevření Nastavení
        available_voices: list[(voice_id, voice_name)] pro výběr hlasu, nebo None
        is_screen_reader: pokud True, hlasové ovládací prvky jsou disabled
    """

    def __init__(self, current_config, parent=None, first_run: bool = False,
                 available_voices=None, is_screen_reader: bool = False):
        super().__init__(parent)
        self._first_run = first_run
        self.config = dict(current_config)  # kopie, neměnit originál před accept

        # --- Název dialogu ---
        if first_run:
            self.setWindowTitle("Vítejte – prvotní nastavení")
            desc = "Prvotní nastavení aplikace. Nastavte hlas a hlášení. Všechny volby lze později změnit přes Nastavení (Ctrl+Shift+Q)."
        else:
            self.setWindowTitle("Nastavení")
            desc = "Umožňuje nastavit hlas, rychlost, hlasitost, režim hlášení a podrobnosti hlášení seznamů."
        self.setModal(True)
        self.setMinimumWidth(450)
        self.setAccessibleName("Vítejte – prvotní nastavení" if first_run else "Dialog nastavení aplikace")
        self.setAccessibleDescription(desc)

        self.layout = QVBoxLayout(self)

        # Informativní label pro first_run (pouze vizuální + přístupnost)
        if first_run:
            info_label = QLabel("Toto je prvotní nastavení. Všechny volby lze později kdykoli změnit přes Nastavení (Ctrl+Shift+Q) nebo z ikonky v oznamovací oblasti.")
            info_label.setWordWrap(True)
            info_label.setAccessibleName("Informace o prvotním nastavení")
            info_label.setAccessibleDescription("Všechny volby lze později změnit přes Nastavení klávesovou zkratkou Ctrl Shift Q nebo z oznamovací oblasti.")
            self.layout.addWidget(info_label)

        self.form_layout = QFormLayout()

        # --- Hlasový výstup (SAPI hlas) ---
        self.voice_combo = None
        if available_voices is not None:
            # available_voices: list of (id, name)
            self.voice_combo = QComboBox()
            self.voice_combo.setAccessibleName("Hlasový výstup")
            self.voice_combo.setAccessibleDescription("Výběr SAPI hlasu. Použije se pouze pokud neběží odečítač obrazovky jako NVDA.")
            # naplnit
            if not available_voices:
                self.voice_combo.addItem("Výchozí hlas (žádné další hlasy nenalezeny)", None)
                self.voice_combo.setEnabled(False)
            else:
                for vid, vname in available_voices:
                    self.voice_combo.addItem(vname, vid)
                # nastavit aktuální podle config
                current_voice = self.config.get("voice_id")
                idx = 0
                if current_voice:
                    for i in range(self.voice_combo.count()):
                        if self.voice_combo.itemData(i) == current_voice:
                            idx = i
                            break
                self.voice_combo.setCurrentIndex(idx)
            if is_screen_reader:
                self.voice_combo.setEnabled(False)
                self.voice_combo.setAccessibleDescription("Výběr hlasu je vypnutý, protože běží odečítač obrazovky. Hlas zajišťuje odečítač.")
                self.voice_label = QLabel("Hlasový výstup (vypnuto – běží odečítač):")
            else:
                self.voice_label = QLabel("Hlasový výstup:")
            self.voice_label.setBuddy(self.voice_combo)
            self.form_layout.addRow(self.voice_label, self.voice_combo)

        # --- Rychlost hlasu ---
        self.rate_spin = QSpinBox()
        self.rate_spin.setRange(50, 500)
        self.rate_spin.setSingleStep(10)
        self.rate_spin.setValue(self.config.get("rate", 150))
        self.rate_spin.setAccessibleName("Rychlost hlasu")
        self.rate_spin.setAccessibleDescription("Nastavuje rychlost mluveného slova v slovech za minutu. Rozsah 50 až 500.")
        if is_screen_reader:
            self.rate_spin.setEnabled(False)
            self.rate_spin.setAccessibleDescription("Rychlost je vypnutá, protože běží odečítač obrazovky.")
        self.rate_label = QLabel("Rychlost hlasu:")
        self.rate_label.setBuddy(self.rate_spin)
        self.form_layout.addRow(self.rate_label, self.rate_spin)

        # --- Hlasitost ---
        self.volume_spin = QDoubleSpinBox()
        self.volume_spin.setRange(0.0, 1.0)
        self.volume_spin.setSingleStep(0.1)
        self.volume_spin.setDecimals(1)
        self.volume_spin.setValue(self.config.get("volume", 1.0))
        self.volume_spin.setAccessibleName("Hlasitost")
        self.volume_spin.setAccessibleDescription("Nastavuje hlasitost od 0 do 1. Krok 0,1.")
        if is_screen_reader:
            self.volume_spin.setEnabled(False)
            self.volume_spin.setAccessibleDescription("Hlasitost je vypnutá, protože běží odečítač obrazovky.")
        self.volume_label = QLabel("Hlasitost:")
        self.volume_label.setBuddy(self.volume_spin)
        self.form_layout.addRow(self.volume_label, self.volume_spin)

        # --- Režim hlášení ---
        self.report_combo = QComboBox()
        self.report_combo.addItems(["Všechny odstavce", "Pouze seznamy"])
        self.report_combo.setCurrentIndex(1 if self.config.get("reporting_mode", False) else 0)
        self.report_combo.setAccessibleName("Režim hlášení")
        self.report_combo.setAccessibleDescription("Určuje, zda se má hlásit pouze obsah seznamů, nebo i normální text mimo seznamy.")
        self.report_label = QLabel("Režim hlášení:")
        self.report_label.setBuddy(self.report_combo)
        self.form_layout.addRow(self.report_label, self.report_combo)

        # --- Silent mode ---
        self.silent_check = QCheckBox("Zapnout tichý režim při psaní")
        self.silent_check.setChecked(self.config.get("silent_mode", True))
        self.silent_check.setAccessibleName("Tichý režim při psaní")
        self.silent_check.setAccessibleDescription("Pokud je zaškrtnuto, aplikace přestane mluvit při psaní na klávesnici.")
        self.form_layout.addRow(self.silent_check)

        self.layout.addLayout(self.form_layout)

        # --- Skupina: Podrobnosti hlášení seznamu ---
        self.details_group = QGroupBox("Podrobnosti hlášení seznamu")
        self.details_group.setAccessibleName("Podrobnosti hlášení seznamu")
        self.details_group.setAccessibleDescription("Zaškrtněte, které informace se mají hlásit u položek seznamu.")
        group_layout = QVBoxLayout(self.details_group)

        self.announce_list_type_check = QCheckBox("Hlásit typ seznamu")
        self.announce_list_type_check.setChecked(self.config.get("announce_list_type", True))
        self.announce_list_type_check.setAccessibleName("Hlásit typ seznamu")
        self.announce_list_type_check.setAccessibleDescription("Pokud je zaškrtnuto, hlásí se zda jde o položku seznamu nebo text mimo seznam.")

        self.announce_level_check = QCheckBox("Hlásit úroveň")
        self.announce_level_check.setChecked(self.config.get("announce_level", True))
        self.announce_level_check.setAccessibleName("Hlásit úroveň")
        self.announce_level_check.setAccessibleDescription("Pokud je zaškrtnuto, hlásí se úroveň vnoření položky seznamu.")

        self.announce_index_check = QCheckBox("Hlásit pořadí v seznamu")
        self.announce_index_check.setChecked(self.config.get("announce_index", True))
        self.announce_index_check.setAccessibleName("Hlásit pořadí v seznamu")
        self.announce_index_check.setAccessibleDescription("Pokud je zaškrtnuto, hlásí se pořadí položky mezi sourozenci, například 2 z 5.")

        self.announce_subitems_check = QCheckBox("Hlásit počet podpoložek")
        self.announce_subitems_check.setChecked(self.config.get("announce_subitems", True))
        self.announce_subitems_check.setAccessibleName("Hlásit počet podpoložek")
        self.announce_subitems_check.setAccessibleDescription("Pokud je zaškrtnuto, hlásí se počet vnořených podpoložek.")

        group_layout.addWidget(self.announce_list_type_check)
        group_layout.addWidget(self.announce_level_check)
        group_layout.addWidget(self.announce_index_check)
        group_layout.addWidget(self.announce_subitems_check)

        self.layout.addWidget(self.details_group)

        # --- Tlačítka (QDialogButtonBox pro standardní role a Esc) ---
        self.button_box = QDialogButtonBox(self)
        if first_run:
            self.ok_btn = self.button_box.addButton("Uložit a pokračovat", QDialogButtonBox.ButtonRole.AcceptRole)
            self.ok_btn.setAccessibleName("Uložit a pokračovat")
            self.ok_btn.setAccessibleDescription("Uloží nastavení a spustí aplikaci")
            self.cancel_btn = self.button_box.addButton("Ukončit", QDialogButtonBox.ButtonRole.RejectRole)
            self.cancel_btn.setAccessibleName("Ukončit")
            self.cancel_btn.setAccessibleDescription("Ukončí aplikaci bez uložení")
        else:
            self.ok_btn = self.button_box.addButton("Uložit", QDialogButtonBox.ButtonRole.AcceptRole)
            self.ok_btn.setAccessibleName("Uložit")
            self.ok_btn.setAccessibleDescription("Uloží nastavení a zavře dialog")
            self.cancel_btn = self.button_box.addButton("Zrušit", QDialogButtonBox.ButtonRole.RejectRole)
            self.cancel_btn.setAccessibleName("Zrušit")
            self.cancel_btn.setAccessibleDescription("Zavře dialog bez uložení změn")

        self.ok_btn.setDefault(True)
        self.cancel_btn.setAutoDefault(False)

        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        self.layout.addWidget(self.button_box)

        # --- Tab order ---
        # Zjistit první fokusovatelný prvek
        first_widget = self.voice_combo if self.voice_combo is not None else self.rate_spin
        # Sestavit pořadí
        order = []
        if self.voice_combo is not None:
            order.append(self.voice_combo)
        order.extend([self.rate_spin, self.volume_spin, self.report_combo, self.silent_check,
                      self.announce_list_type_check, self.announce_level_check,
                      self.announce_index_check, self.announce_subitems_check])
        # nastavit tab order postupně
        for a, b in zip(order, order[1:]):
            self.setTabOrder(a, b)
        if order:
            self.setTabOrder(order[-1], self.ok_btn)
            self.setTabOrder(self.ok_btn, self.cancel_btn)

        # Focus na první pole pro rychlou NVDA navigaci
        first_widget.setFocus()

    def get_config(self):
        cfg = dict(self.config)  # vychází z původní kopie, přepíše hodnoty z UI
        cfg["rate"] = self.rate_spin.value()
        cfg["volume"] = self.volume_spin.value()
        cfg["reporting_mode"] = self.report_combo.currentIndex() == 1
        cfg["silent_mode"] = self.silent_check.isChecked()
        cfg["announce_list_type"] = self.announce_list_type_check.isChecked()
        cfg["announce_level"] = self.announce_level_check.isChecked()
        cfg["announce_index"] = self.announce_index_check.isChecked()
        cfg["announce_subitems"] = self.announce_subitems_check.isChecked()
        if self.voice_combo is not None:
            cfg["voice_id"] = self.voice_combo.currentData()
        return cfg
