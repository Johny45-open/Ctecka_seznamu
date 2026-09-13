from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QComboBox, 
                             QCheckBox, QSpinBox, QDoubleSpinBox, QPushButton, 
                             QHBoxLayout, QFormLayout)
from PyQt6.QtCore import Qt

class SettingsDialog(QDialog):
    def __init__(self, current_config, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nastavení aplikace")
        self.setMinimumWidth(400)
        self.setModal(True)
        self.setAccessibleName("Dialog nastavení aplikace")
        self.setAccessibleDescription("Umožňuje nastavit rychlost a hlasitost hlasu, režim hlášení a tichý režim při psaní.")
        
        self.config = current_config
        self.layout = QVBoxLayout(self)
        self.form_layout = QFormLayout()
        
        # --- Nastavení ---
        
        # Rychlost hlasu
        self.rate_spin = QSpinBox()
        self.rate_spin.setRange(50, 500)
        self.rate_spin.setValue(self.config.get("rate", 150))
        self.rate_spin.setAccessibleName("Rychlost hlasu")
        self.rate_spin.setAccessibleDescription("Nastavuje rychlost mluveného slova v slovech za minutu. Rozsah 50 až 500.")
        self.rate_label = QLabel("Rychlost hlasu:")
        self.rate_label.setBuddy(self.rate_spin)
        self.form_layout.addRow(self.rate_label, self.rate_spin)
        
        # Hlasitost
        self.volume_spin = QDoubleSpinBox()
        self.volume_spin.setRange(0.0, 1.0)
        self.volume_spin.setSingleStep(0.1)
        self.volume_spin.setValue(self.config.get("volume", 1.0))
        self.volume_spin.setAccessibleName("Hlasitost")
        self.volume_spin.setAccessibleDescription("Nastavuje hlasitost od 0 do 1.")
        self.volume_label = QLabel("Hlasitost:")
        self.volume_label.setBuddy(self.volume_spin)
        self.form_layout.addRow(self.volume_label, self.volume_spin)
        
        # Režim hlášení
        self.report_combo = QComboBox()
        self.report_combo.addItems(["Všechny odstavce", "Pouze seznamy"])
        self.report_combo.setCurrentIndex(1 if self.config.get("reporting_mode", False) else 0)
        self.report_combo.setAccessibleName("Režim hlášení")
        self.report_combo.setAccessibleDescription("Určuje, zda se má hlásit pouze obsah seznamů, nebo i normální text.")
        self.report_label = QLabel("Režim hlášení:")
        self.report_label.setBuddy(self.report_combo)
        self.form_layout.addRow(self.report_label, self.report_combo)
        
        # Silent mode
        self.silent_check = QCheckBox("Zapnout tichý režim při psaní")
        self.silent_check.setChecked(self.config.get("silent_mode", True))
        self.silent_check.setAccessibleName("Tichý režim při psaní")
        self.silent_check.setAccessibleDescription("Pokud je zaškrtnuto, aplikace přestane mluvit při psaní.")
        self.form_layout.addRow(self.silent_check)
        
        self.layout.addLayout(self.form_layout)
        
        # --- Tlačítka ---
        self.btn_layout = QHBoxLayout()
        self.ok_btn = QPushButton("Uložit")
        self.ok_btn.setAccessibleName("Uložit")
        self.ok_btn.setAccessibleDescription("Uloží nastavení a zavře dialog")
        self.ok_btn.setDefault(True)

        self.cancel_btn = QPushButton("Zrušit")
        self.cancel_btn.setAccessibleName("Zrušit")
        self.cancel_btn.setAccessibleDescription("Zavře dialog bez uložení změn")
        self.cancel_btn.setAutoDefault(False)
        
        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)
        
        self.btn_layout.addWidget(self.ok_btn)
        self.btn_layout.addWidget(self.cancel_btn)
        self.layout.addLayout(self.btn_layout)

        # Tab order: rate -> volume -> report_combo -> silent_check -> Uložit -> Zrušit
        self.setTabOrder(self.rate_spin, self.volume_spin)
        self.setTabOrder(self.volume_spin, self.report_combo)
        self.setTabOrder(self.report_combo, self.silent_check)
        self.setTabOrder(self.silent_check, self.ok_btn)
        self.setTabOrder(self.ok_btn, self.cancel_btn)

        # Focus na první pole pro rychlou NVDA navigaci
        self.rate_spin.setFocus()
        
    def get_config(self):
        return {
            "rate": self.rate_spin.value(),
            "volume": self.volume_spin.value(),
            "reporting_mode": self.report_combo.currentIndex() == 1,
            "silent_mode": self.silent_check.isChecked()
        }
