#!/bin/env python3

import os
import sys
from mosaic import MosaicoRTSP

from qtcompat import (
    QPixmap,
    QIcon,
    QTimer,
    QApplication,
    QSplashScreen,
    Qt_AlignmentFlag_AlignBottom,
    Qt_AlignmentFlag_AlignCenter,
    Qt_Color_White,
    Qt_WindowType_FramelessWindowHint,
    Qt_WindowType_WindowStaysOnTopHint,
    QT_COMPAT_VERSION,
)


def prevent_screensaver():
    os.system("xdg-screensaver reset")


if __name__ == "__main__":
    app = QApplication(sys.argv)

    app.setWindowIcon(
        QIcon(os.path.join(os.path.dirname(__file__), "rtsp-client-icon.png"))
    )

    file_path = os.path.realpath(__file__)

    pixmap = QPixmap(os.path.join(os.path.dirname(file_path), "_splashscreen.png"))

    # splash = QSplashScreen(pixmap)
    splash = QSplashScreen(
        pixmap, Qt_WindowType_WindowStaysOnTopHint | Qt_WindowType_FramelessWindowHint
    )
    splash.showMessage(
        "Carregando Câmeras...",
        Qt_AlignmentFlag_AlignBottom | Qt_AlignmentFlag_AlignCenter,
        Qt_Color_White,
    )
    splash.show()

    QApplication.processEvents()

    timer = QTimer()
    timer.timeout.connect(prevent_screensaver)
    timer.start(30000)  # a cada 30s
    window = MosaicoRTSP()
    window.showMaximized()

    splash.finish(window)  # fecha o splash depois que a janela abriu
    if QT_COMPAT_VERSION == 6:
        sys.exit(app.exec())

    else:
        sys.exit(app.exec_())
