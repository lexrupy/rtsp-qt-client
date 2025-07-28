import os

from qtcompat import (
    QLabel,
    QPushButton,
    QPixmap,
    QVBoxLayout,
    QDialog,
    Qt_AlignmentFlag_AlignCenter,
    Qt_AspectRatioMode_KeepAspectRatio,
    Qt_TransformationMode_SmoothTransformation,
    QT_COMPAT_VERSION,
    QT_VERSION_STR,
)


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sobre o Aplicativo")
        self.resize(400, 200)

        layout = QVBoxLayout(self)

        # Caminho do ícone (ajusta conforme o nome do seu ícone)
        icon_path = os.path.join(os.path.dirname(__file__), "rtsp-client-icon.svg")
        if os.path.exists(icon_path):
            pixmap = QPixmap(icon_path)
            icon_label = QLabel()
            icon_label.setPixmap(
                pixmap.scaled(
                    64,
                    64,
                    Qt_AspectRatioMode_KeepAspectRatio,
                    Qt_TransformationMode_SmoothTransformation,
                )
            )
            icon_label.setAlignment(Qt_AlignmentFlag_AlignCenter)
            layout.addWidget(icon_label)
        app_info = QLabel(
            f"""
        <h2 style='margin: 4px;'>Mosaico RTSP</h2>
        <p>Aplicativo para exibição simultânea de múltiplas câmeras via RTSP.</p>
        <p><b>Versão do Qt:</b> {QT_VERSION_STR}</p>
        <p>Desenvolvido por Alexandre</p>
        """
        )
        # app_info = QLabel("Mosaico RTSP\nVersão 1.0\n© 2025 Alexandre")
        app_info.setAlignment(Qt_AlignmentFlag_AlignCenter)
        layout.addWidget(app_info)

        qt_version_str = f"Qt Version: {'6' if QT_COMPAT_VERSION == 6 else '5'}"
        qt_label = QLabel(qt_version_str)
        qt_label.setAlignment(Qt_AlignmentFlag_AlignCenter)
        layout.addWidget(qt_label)

        btn_close = QPushButton("Fechar")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)
