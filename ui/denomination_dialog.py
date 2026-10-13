from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QSpinBox, QPushButton, QFormLayout, QGroupBox, QDoubleSpinBox, QMessageBox
)
from PyQt6.QtCore import Qt

class DenominationDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("جرد الدرج (Blind Closure)")
        self.resize(350, 450)
        self.layout = QVBoxLayout(self)
        
        info = QLabel("أدخل عدد الأوراق النقدية لكل فئة:")
        info.setStyleSheet("font-weight: bold; font-size: 14px; margin-bottom: 10px;")
        self.layout.addWidget(info)
        
        self.denominations = [200, 100, 50, 20, 10, 5, 1, 0.5]
        self.spinboxes = {}
        
        form_group = QGroupBox("فئات الكاش")
        form_layout = QFormLayout(form_group)
        
        for denom in self.denominations:
            spin = QSpinBox()
            spin.setRange(0, 10000)
            spin.setFixedSize(100, 30)
            spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
            spin.valueChanged.connect(self._update_total)
            self.spinboxes[denom] = spin
            
            label_text = f"فئة {denom} جنيه:" if denom >= 1 else f"فئة {denom*100} قرش:"
            form_layout.addRow(QLabel(label_text), spin)
            
        self.layout.addWidget(form_group)
        
        self.total_label = QLabel("إجمالي الكاش: 0.00 ج.م")
        self.total_label.setStyleSheet("font-weight: bold; font-size: 16px; color: #7C3AED;")
        self.layout.addWidget(self.total_label)
        
        card_group = QGroupBox("إجمالي فيزا / شبكة")
        card_layout = QHBoxLayout(card_group)
        self.card_spin = QDoubleSpinBox()
        self.card_spin.setRange(0, 1000000)
        self.card_spin.setDecimals(2)
        self.card_spin.setFixedSize(150, 30)
        card_layout.addWidget(QLabel("إيصالات الفيزا:"))
        card_layout.addWidget(self.card_spin)
        self.layout.addWidget(card_group)
        
        btn_layout = QHBoxLayout()
        submit_btn = QPushButton("تأكيد وإغلاق الدرج")
        submit_btn.setStyleSheet("background-color: #10B981; color: white; padding: 8px; font-weight: bold; border-radius: 4px;")
        submit_btn.clicked.connect(self.accept)
        
        cancel_btn = QPushButton("إلغاء")
        cancel_btn.setStyleSheet("background-color: #EF4444; color: white; padding: 8px; border-radius: 4px;")
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(submit_btn)
        btn_layout.addWidget(cancel_btn)
        self.layout.addLayout(btn_layout)
        
    def _update_total(self):
        total = sum(denom * spin.value() for denom, spin in self.spinboxes.items())
        self.total_label.setText(f"إجمالي الكاش: {total:,.2f} ج.م")

    def get_results(self):
        details = {str(denom): spin.value() for denom, spin in self.spinboxes.items() if spin.value() > 0}
        total_cash = sum(denom * spin.value() for denom, spin in self.spinboxes.items())
        return total_cash, self.card_spin.value(), details
