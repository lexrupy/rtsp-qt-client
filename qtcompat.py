try:
    from PyQt6.QtWidgets import (
        QApplication,
        QWidget,
        QLabel,
        QLineEdit,
        QPushButton,
        QGridLayout,
        QVBoxLayout,
        QHBoxLayout,
        QMessageBox,
        QInputDialog,
        QDialog,
        QIcon,
        QMenu,
        QSplashScreen,
        QSizePolicy,
    )
    from PyQt6.QtGui import QImage, QPixmap, QDrag, QAction
    from PyQt6.QtCore import (
        QTimer,
        Qt,
        QMimeData,
        QSize,
        QThread,
        pyqtSignal,
        QT_VERSION_STR,
        QWIDGETSIZE_MAX as _QWIDGETSIZE_MAX,
    )

    Qt_WindowType_FramelessWindowHint = Qt.WindowType.FramelessWindowHint
    Qt_WindowType_WindowStaysOnTopHint = Qt.WindowType.WindowStaysOnTopHint
    Qt_AlignmentFlag_AlignBottom = Qt.AlignmentFlag.AlignBottom
    Qt_AlignmentFlag_AlignCenter = Qt.AlignmentFlag.AlignCenter
    Qt_Color_White = Qt.GlobalColor.white
    Qt_Color_Black = Qt.GlobalColor.black

    Qt_AspectRatioMode_KeepAspectRatio = Qt.AspectRatioMode.KeepAspectRatio
    Qt_TransformationMode_SmoothTransformation = (
        Qt.TransformationMode.SmoothTransformation
    )

    Qt_Key_F = Qt.Key.Key_F
    Qt_Key_F11 = Qt.Key.Key_F11
    Qt_Key_Escape = Qt.Key.Key_Escape
    Qt_KeyModifier_Control = Qt.KeyboardModifier.ControlModifier
    Qt_LeftButton = Qt.MouseButton.LeftButton
    Qt_MoveAction = Qt.DropAction.MoveAction

    QDialog_Accepted = QDialog.DialogCode.Accepted

    QMessageBox_Yes = QMessageBox.StandardButton.Yes
    QMessageBox_No = QMessageBox.StandardButton.No
    QMessageBox_Cancel = QMessageBox.StandardButton.Cancel

    QImage_Format_RGB888 = QImage.Format.Format_RGB888

    QSizePolicy_Expanding = QSizePolicy.Policy.Expanding

    QT_COMPAT_VERSION = 6

    QWIDGETSIZE_MAX = _QWIDGETSIZE_MAX

    def Qt_Compat_GetMousePoint(e):
        return e.globalPosition().toPoint()

except:
    from PyQt5.QtWidgets import (
        QApplication,
        QWidget,
        QLabel,
        QLineEdit,
        QPushButton,
        QGridLayout,
        QVBoxLayout,
        QHBoxLayout,
        QMessageBox,
        QInputDialog,
        QDialog,
        QMenu,
        QAction,
        QSplashScreen,
        QSizePolicy,
    )
    from PyQt5.QtGui import QImage, QPixmap, QDrag, QIcon
    from PyQt5.QtCore import (
        QTimer,
        Qt,
        QMimeData,
        QThread,
        QSize,
        pyqtSignal,
        QT_VERSION_STR,
    )

    Qt_WindowType_FramelessWindowHint = Qt.FramelessWindowHint
    Qt_WindowType_WindowStaysOnTopHint = Qt.WindowStaysOnTopHint

    Qt_AspectRatioMode_KeepAspectRatio = Qt.AspectRatioMode.KeepAspectRatio
    Qt_TransformationMode_SmoothTransformation = (
        Qt.TransformationMode.SmoothTransformation
    )

    Qt_AlignmentFlag_AlignBottom = Qt.AlignBottom
    Qt_AlignmentFlag_AlignCenter = Qt.AlignCenter
    Qt_Color_White = Qt.white
    Qt_Color_Black = Qt.black

    Qt_Key_F = Qt.Key_F
    Qt_Key_F11 = Qt.Key_F11
    Qt_Key_Escape = Qt.Key_Escape
    Qt_KeyModifier_Control = Qt.ControlModifier
    Qt_LeftButton = Qt.LeftButton
    Qt_MoveAction = Qt.MoveAction

    QDialog_Accepted = QDialog.Accepted

    QMessageBox_Yes = QMessageBox.Yes
    QMessageBox_No = QMessageBox.No
    QMessageBox_Cancel = QMessageBox.Cancel

    QSizePolicy_Expanding = QSizePolicy.Expanding

    QT_COMPAT_VERSION = 5
    QWIDGETSIZE_MAX = 16777215

    QImage_Format_RGB888 = QImage.Format_RGB888

    def Qt_Compat_GetMousePoint(e):
        return e.globalPos()


__all__ = [
    "QApplication",
    "QWidget",
    "QLabel",
    "QIcon",
    "QSize",
    "QGridLayout",
    "QVBoxLayout",
    "QHBoxLayout",
    "QMessageBox",
    "QInputDialog",
    "QDialog",
    "QLineEdit",
    "QPushButton",
    "QMenu",
    "QSplashScreen",
    "QImage",
    "QPixmap",
    "QDrag",
    "QAction",
    "QTimer",
    "Qt",
    "QMimeData",
    "QThread",
    "QSizePolicy_Expanding",
    "pyqtSignal",
    "QT_COMPAT_VERSION",
    "QT_VERSION_STR",
    "QWIDGETSIZE_MAX",
]
