from qtcompat import (
    QLabel,
    QLineEdit,
    QPushButton,
    QComboBox,
    QHBoxLayout,
    QVBoxLayout,
    QMessageBox,
    QDialog,
)


class AddCameraDialog(QDialog):
    def __init__(self, parent=None, stream_type="Auto", editing=False):
        super().__init__(parent)
        self.edigint = editing
        if editing:
            title = "Editar Câmera"
        else:
            title = "Adicionar Câmera"
        self.setWindowTitle(title)
        self.resize(700, 160)  # Largura x Altura
        self.low_url = ""
        self.high_url = ""
        self.stream_type = stream_type

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("URL Low Resolution:"))
        self.low_url_edit = QLineEdit(self)
        layout.addWidget(self.low_url_edit)

        layout.addWidget(QLabel("URL High Resolution:"))
        self.high_url_edit = QLineEdit(self)
        layout.addWidget(self.high_url_edit)

        # layout.addWidget(QLabel("Tipo de captura:"))
        # self.stream_type_combo = QComboBox(self)
        # self.stream_type_combo.addItems(
        #     ["Auto", "OpenCV", "GStreamer", "Ffmpeg", "DirectShow", "MSMF"]
        # )
        # self.stream_type_combo.setCurrentText(self.stream_type)
        # layout.addWidget(self.stream_type_combo)
        combo_layout = QHBoxLayout()
        self.stream_type_combo = QComboBox(self)
        self.stream_type_combo.addItems(
            ["Auto", "OpenCV", "GStreamer", "Ffmpeg", "DirectShow", "MSMF"]
        )
        self.stream_type_combo.setCurrentText(self.stream_type)
        combo_layout.addWidget(self.stream_type_combo)

        if editing:
            self.restart_label = QLabel(" (necessário reiniciar aplicativo)", self)
            self.restart_label.setStyleSheet("color: red; font-weight: bold;")
            combo_layout.addWidget(self.restart_label)

        layout.addLayout(combo_layout)

        btn_layout = QHBoxLayout()
        self.ok_btn = QPushButton("OK", self)
        self.cancel_btn = QPushButton("Cancelar", self)
        btn_layout.addWidget(self.ok_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)

    def accept(self):
        low_url = self.low_url_edit.text().strip()
        high_url = self.high_url_edit.text().strip()
        if not low_url or not high_url:
            QMessageBox.warning(self, "Erro", "Ambas as URLs devem ser preenchidas.")
            return
        self.low_url = low_url
        self.high_url = high_url
        self.stream_type = self.stream_type_combo.currentText()
        super().accept()
