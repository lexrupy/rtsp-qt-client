#!/bin/env python3

import os
import math
import time
import sys
import cv2
import configparser

from qtcompat import (
    QLabel,
    QLineEdit,
    QPushButton,
    QImage,
    QPixmap,
    QApplication,
    QDrag,
    QMimeData,
    QWidget,
    QGridLayout,
    QHBoxLayout,
    QVBoxLayout,
    QMessageBox,
    QDialog,
    QMenu,
    QAction,
    QSplashScreen,
    QThread,
    pyqtSignal,
    QMessageBox_No,
    QMessageBox_Yes,
    QDialog_Accepted,
    Qt_AlignmentFlag_AlignBottom,
    Qt_AlignmentFlag_AlignCenter,
    Qt_AspectRatioMode_KeepAspectRatio,
    Qt_Color_White,
    Qt_Key_Escape,
    Qt_Key_F,
    Qt_Key_F11,
    Qt_KeyModifier_Control,
    Qt_TransformationMode_SmoothTransformation,
    Qt_WindowType_FramelessWindowHint,
    Qt_WindowType_WindowStaysOnTopHint,
    Qt_LeftButton,
    Qt_MoveAction,
    Qt_Compat_GetMousePoint,
    QImage_Format_RGB888,
    QT_COMPAT_VERSION,
    QT_VERSION_STR,
)


CONFIG_FILE = os.path.expanduser("~/.config/rtsp-qt-client/config.ini")


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
        <p>Desenvolvido por Alexandre - {os.uname().nodename}</p>
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


class AddCameraDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Adicionar/Editar Câmera")
        self.resize(700, 160)  # Largura x Altura
        self.low_url = ""
        self.high_url = ""

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("URL Low Resolution:"))
        self.low_url_edit = QLineEdit(self)
        layout.addWidget(self.low_url_edit)

        layout.addWidget(QLabel("URL High Resolution:"))
        self.high_url_edit = QLineEdit(self)
        layout.addWidget(self.high_url_edit)

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
        super().accept()


class CameraThread(QThread):
    frame_ready = pyqtSignal(QImage)
    connection_failed = pyqtSignal()

    def __init__(self, url):
        super().__init__()
        self.url = url
        self.running = True

    def run(self):

        gst = (
            f"rtspsrc location={self.url} latency=0 ! "
            "rtph264depay ! avdec_h264 ! videoconvert ! appsink sync=false"
        )
        cap = cv2.VideoCapture(gst, cv2.CAP_GSTREAMER)
        if not cap.isOpened():
            self.connection_failed.emit()
            return

        while self.running:
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.01)
                continue
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb.shape
            bytesPerLine = ch * w
            image = QImage(rgb.data, w, h, bytesPerLine, QImage_Format_RGB888)
            self.frame_ready.emit(image)

        cap.release()

    def stop(self):
        self.running = False
        self.wait()


class CameraViewer(QLabel):
    def __init__(self, camera, url_low=None, url_high=None):
        super().__init__()
        self.camera_id = camera
        self.url_low = url_low if url_low else ""
        self.url_high = url_high if url_high else ""
        self.setScaledContents(True)
        self.setAlignment(Qt_AlignmentFlag_AlignCenter)
        self.setText("Conectando...")
        self.setStyleSheet("background-color: black; color: white; font-size: 16px;")
        self.last_esc_time = 0
        self.thread = None
        self.current_url = self.url_low
        self.init_capture()

    def init_capture(self):
        self.thread = CameraThread(self.current_url)
        self.thread.frame_ready.connect(self.update_frame)
        self.thread.connection_failed.connect(self.show_connection_error)
        self.thread.start()

    def change_res(self, res=0):
        new_url = self.url_high if res == 0 else self.url_low
        self.set_url(new_url)

    def set_url(self, new_url):
        if not new_url or new_url == self.current_url:
            return  # Nada a fazer se for a mesma URL
        self.current_url = new_url
        if self.thread:
            self.thread.stop()
            self.thread.wait()
        self.init_capture()

    def update_frame(self, img):
        self.setPixmap(
            QPixmap.fromImage(img).scaled(
                self.size(),
                Qt_AspectRatioMode_KeepAspectRatio,
                Qt_TransformationMode_SmoothTransformation,
            )
        )

    def show_connection_error(self):
        self.setText("Erro ao conectar")

    def close(self):
        if self.thread:
            self.thread.stop()

    def mouseDoubleClickEvent(self, event):
        self.parent().toggle_fullscreen(self)

    def dragEnterEvent(self, e):
        if e.mimeData().hasText():
            e.acceptProposedAction()

    def dropEvent(self, e):
        if not e.mimeData().hasText():
            return
        cam_id = int(e.mimeData().text())
        parent = self.parent()
        source = next((v for v in parent.viewers if v.camera_id == cam_id), None)
        target = self
        if source and source != target:
            parent.swap_viewers(source, target)
        e.acceptProposedAction()

    def mousePressEvent(self, e):
        if e.button() == Qt_LeftButton:
            self.drag_start_pos = Qt_Compat_GetMousePoint(e)

    def mouseMoveEvent(self, e):
        if (e.buttons() & Qt_LeftButton) and (
            Qt_Compat_GetMousePoint(e) - self.drag_start_pos
        ).manhattanLength() > QApplication.startDragDistance():
            drag = QDrag(self)
            mime = QMimeData()
            mime.setText(str(self.camera_id))
            drag.setMimeData(mime)
            drag.exec(Qt_MoveAction)


class MosaicoRTSP(QWidget):
    def __init__(self):
        super().__init__()
        self.cameras = []
        self.config = configparser.ConfigParser()
        self.load_config()

        self.viewers = []
        self._last_esc_time = 0
        self.setWindowTitle("Mosaico RTSP")
        self.layout = QGridLayout(self)
        self.setLayout(self.layout)
        self.layout.setSpacing(1)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.viewers = []
        self.fullscreen_mode = False
        self.original_positions = {}
        self.current_fullscreen = None

        self.selected_viewer = None

        self.reload_cameras()

    def show_about_dialog(self):
        dlg = AboutDialog(self)
        dlg.exec()

    def add_camera_dialog(self):
        dlg = AddCameraDialog(self)
        if dlg.exec() == QDialog_Accepted:
            low_url = dlg.low_url
            high_url = dlg.high_url
            self.add_camera_with_urls(low_url, high_url)

    def copy_camera_dialog(self):
        if not self.selected_viewer:
            return

        cam_id = self.selected_viewer.camera_id
        cam_data = next((c for c in self.cameras if c["id"] == cam_id), None)
        if not cam_data:
            return

        dlg = AddCameraDialog(self)
        dlg.low_url_edit.setText(cam_data["url_low"])
        dlg.high_url_edit.setText(cam_data["url_high"])

        if dlg.exec() == QDialog_Accepted:
            low_url = dlg.low_url
            high_url = dlg.high_url
            self.add_camera_with_urls(low_url, high_url)

    def edit_camera_dialog(self):
        if not self.selected_viewer:
            return
        viewer = self.selected_viewer
        cam_id = viewer.camera_id
        cam_data = next((c for c in self.cameras if c["id"] == cam_id), None)
        if not cam_data:
            return
        dlg = AddCameraDialog(self)
        dlg.low_url_edit.setText(cam_data["url_low"])
        dlg.high_url_edit.setText(cam_data["url_high"])
        if dlg.exec() == QDialog_Accepted:
            cam_data["url_low"] = dlg.low_url
            cam_data["url_high"] = dlg.high_url
            self.save_config()
            self.reload_cameras()

    def add_camera_with_urls(self, low_url, high_url):
        # Acha um ID disponível para a nova câmera, ex: o próximo inteiro livre
        # new_cam_id = max(self.cameras) + 1 if self.cameras else 1
        new_cam_id = max(cam["id"] for cam in self.cameras) + 1 if self.cameras else 1
        self.cameras.append(
            {"id": new_cam_id, "url_low": low_url, "url_high": high_url}
        )
        self.save_config()
        self.reload_cameras()

    def toggle_fullscreen(self, viewer):
        if not self.fullscreen_mode:
            for v in self.viewers:
                if v != viewer:
                    v.hide()
            viewer.change_res(0)
            self.layout.addWidget(viewer, 0, 0, self.rows, self.cols)
            self.fullscreen_mode = True
            self.current_fullscreen = viewer
        else:
            viewer.change_res(1)
            for v in self.viewers:
                v.show()
            for v, (r, c) in self.original_positions.items():
                self.layout.addWidget(v, r, c)
            self.fullscreen_mode = False
            self.current_fullscreen = None

    def swap_viewers(self, viewer1, viewer2):
        # r1, c1 = self.original_positions[viewer1]
        # r2, c2 = self.original_positions[viewer2]
        #
        # self.layout.removeWidget(viewer1)
        # self.layout.removeWidget(viewer2)
        #
        # self.layout.addWidget(viewer1, r2, c2)
        # self.layout.addWidget(viewer2, r1, c1)
        #
        # self.original_positions[viewer1], self.original_positions[viewer2] = (r2, c2), (
        #     r1,
        #     c1,
        # )
        r1, c1 = self.original_positions[viewer1]
        r2, c2 = self.original_positions[viewer2]

        # Troca os widgets no layout
        self.layout.removeWidget(viewer1)
        self.layout.removeWidget(viewer2)

        self.layout.addWidget(viewer1, r2, c2)
        self.layout.addWidget(viewer2, r1, c1)

        # Atualiza posições no dicionário
        self.original_positions[viewer1], self.original_positions[viewer2] = (r2, c2), (
            r1,
            c1,
        )

        # --- Atualiza a lista self.cameras para persistir ordem ---
        idx1 = next(
            i for i, cam in enumerate(self.cameras) if cam["id"] == viewer1.camera_id
        )
        idx2 = next(
            i for i, cam in enumerate(self.cameras) if cam["id"] == viewer2.camera_id
        )
        self.cameras[idx1], self.cameras[idx2] = self.cameras[idx2], self.cameras[idx1]

        # atualize também self.viewers para manter coerência
        idx_v1 = self.viewers.index(viewer1)
        idx_v2 = self.viewers.index(viewer2)
        self.viewers[idx_v1], self.viewers[idx_v2] = (
            self.viewers[idx_v2],
            self.viewers[idx_v1],
        )

        self.save_config()

    def reorganize_grid(self):
        count = len(self.viewers)
        if count == 0:
            self.show_no_camera_widget()
            return

        self.cols = int(math.ceil(math.sqrt(count)))
        self.rows = int(math.ceil(count / self.cols))
        self.original_positions.clear()
        for i, viewer in enumerate(self.viewers):
            self.layout.removeWidget(viewer)
            row = i // self.cols
            col = i % self.cols
            self.layout.addWidget(viewer, row, col)
            self.original_positions[viewer] = (row, col)

    def show_no_camera_widget(self):
        # Limpa o grid
        for i in reversed(range(self.layout.count())):
            widget = self.layout.itemAt(i).widget()
            if widget is not None:
                widget.setParent(None)

        label = QLabel("Nenhuma câmera conectada.")
        label.setAlignment(Qt_AlignmentFlag_AlignCenter)
        label.setStyleSheet("font-size: 18px; color: gray;")
        self.layout.addWidget(label, 0, 0)
        self.cols = 0
        self.rows = 0

    def remove_camera(self, cam_id):
        # Encontra o dicionário da câmera com o ID fornecido
        cam_to_remove = next((cam for cam in self.cameras if cam["id"] == cam_id), None)
        if not cam_to_remove:
            print(f"Câmera com id {cam_id} não encontrada na lista.")
            return

        # Remove da lista de câmeras
        self.cameras.remove(cam_to_remove)

        # Encontra o viewer correspondente
        viewer = next((v for v in self.viewers if v.camera_id == cam_id), None)
        if not viewer:
            print(f"Viewer para câmera {cam_id} não encontrado.")
            return

        # Remove do layout e da UI
        self.layout.removeWidget(viewer)
        viewer.close()
        viewer.deleteLater()

        # Remove da lista de viewers
        self.viewers.remove(viewer)

        # Reorganiza o grid e salva a configuração
        self.reorganize_grid()
        self.save_config()

    def add_camera(self, cam):
        if cam in self.cameras:
            return
        viewer = CameraViewer(cam)
        viewer.setAcceptDrops(True)
        self.viewers.append(viewer)
        self.cameras.append(cam)
        # recalcula grid
        count = len(self.cameras)
        self.cols = int(math.ceil(math.sqrt(count)))
        self.rows = int(math.ceil(count / self.cols))
        # adiciona no layout na última posição
        index = len(self.viewers) - 1
        row = index // self.cols
        col = index % self.cols
        viewer.setAcceptDrops(True)
        self.layout.addWidget(viewer, row, col)
        self.original_positions[viewer] = (row, col)
        self.save_config()

    def closeEvent(self, event):
        for viewer in self.viewers:
            if viewer.thread:
                viewer.thread.stop()
                viewer.thread.wait()
            viewer.close()
        event.accept()

    def keyPressEvent(self, event):
        if (event.key() == Qt_Key_F11) or (
            event.key() == Qt_Key_F and event.modifiers() & Qt_KeyModifier_Control
        ):
            # alterna fullscreen da janela inteira
            if self.isFullScreen():
                self.showNormal()
            else:
                self.showFullScreen()

        elif event.key() == Qt_Key_Escape:
            now = time.time()
            if self.fullscreen_mode:
                # Sai do fullscreen do viewer atual
                self.toggle_fullscreen(self.current_fullscreen)
            if hasattr(self, "_last_esc_time") and (now - self._last_esc_time) < 1.0:
                self.do_exit()
            self._last_esc_time = now
        else:
            super().keyPressEvent(event)

    def dragEnterEvent(self, e):
        e.accept()

    def do_exit(self):
        reply = QMessageBox.question(
            self,
            "Encerrar",
            "Deseja realmente sair?",
            QMessageBox_Yes | QMessageBox_No,
            QMessageBox_No,
        )
        if reply == QMessageBox_Yes:
            QApplication.quit()

    def load_config(self):
        self.cameras.clear()
        if os.path.exists(CONFIG_FILE):
            self.config.read(CONFIG_FILE)
            if "Cameras" in self.config and "order" in self.config["Cameras"]:
                cameras_str = self.config["Cameras"]["order"]
                cam_ids = list(map(int, cameras_str.split(",")))
                for cam_id in cam_ids:
                    section = f"Camera{cam_id}"
                    if self.config.has_section(section):
                        url_low = self.config.get(section, "url_low", fallback=None)
                        url_high = self.config.get(section, "url_high", fallback=None)
                        if url_low and url_high:
                            # Monte seu objeto de câmera ou pelo menos um dicionário
                            self.cameras.append(
                                {
                                    "id": cam_id,
                                    "url_low": url_low,
                                    "url_high": url_high,
                                }
                            )
                        else:
                            # URLs faltando, ignore ou trate como desejar
                            pass
                    else:
                        # Seção da câmera não existe, ignore ou trate
                        pass
            else:
                # Configuração vazia, comece com lista vazia
                self.cameras = []
        else:
            # Arquivo config não existe, comece vazio
            self.cameras = []

    def save_config(self):
        if not self.config.has_section("Cameras"):
            self.config.add_section("Cameras")
        # Salva a ordem dos IDs, não o objeto inteiro
        self.config.set(
            "Cameras", "order", ",".join(str(cam["id"]) for cam in self.cameras)
        )

        for cam in self.cameras:
            cam_id = cam["id"]
            section = f"Camera{cam_id}"
            if not self.config.has_section(section):
                self.config.add_section(section)
            self.config.set(section, "url_low", cam.get("url_low", ""))
            self.config.set(section, "url_high", cam.get("url_high", ""))

        config_dir = os.path.dirname(CONFIG_FILE)
        os.makedirs(config_dir, exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            self.config.write(f)

    def contextMenuEvent(self, event):
        widget_clicado = self.childAt(event.pos())
        menu = QMenu(self)
        add_action = QAction("Adicionar câmera", self)
        remove_action = QAction("Remover câmera", self)
        copy_action = QAction("Copiar câmera", self)
        edit_action = QAction("Editar câmera", self)
        about_action = QAction("Sobre...", self)
        exit_action = QAction("Sair", self)
        exit_action.triggered.connect(self.do_exit)
        add_action.triggered.connect(self.add_camera_dialog)
        copy_action.triggered.connect(self.copy_camera_dialog)
        remove_action.triggered.connect(self.remove_camera_dialog)
        edit_action.triggered.connect(self.edit_camera_dialog)
        about_action.triggered.connect(self.show_about_dialog)
        if isinstance(widget_clicado, CameraViewer):
            self.selected_viewer = widget_clicado
            remove_action.setEnabled(True)
            edit_action.setEnabled(True)
            copy_action.setEnabled(True)
        else:
            self.selected_viewer = None
            remove_action.setEnabled(False)
            edit_action.setEnabled(False)
            copy_action.setEnabled(False)
        menu.addAction(add_action)
        menu.addAction(copy_action)
        menu.addAction(edit_action)
        menu.addAction(remove_action)
        menu.addAction(about_action)
        menu.addAction(exit_action)
        menu.exec(event.globalPos())

    def remove_camera_dialog(self):
        if self.selected_viewer is None:
            return
        if not self.cameras:
            return

        reply = QMessageBox.question(
            self,
            "Remover câmera",
            "Deseja remover esta câmera?",
            QMessageBox_Yes | QMessageBox_No,
        )
        if reply == QMessageBox_Yes:
            cam = self.selected_viewer.camera_id
            self.remove_camera(cam)

    def reload_cameras(self):
        # Mapeia viewers existentes por ID
        existing_viewers = {v.camera_id: v for v in self.viewers}
        self.original_positions.clear()
        self.viewers.clear()

        if not self.cameras:
            self.cols = 1
            self.rows = 1
            self.show_no_camera_widget()
            return

        count = len(self.cameras)
        self.cols = int(math.ceil(math.sqrt(count)))
        self.rows = int(math.ceil(count / self.cols))

        # Lista de IDs novos para remoção posterior
        used_ids = set()

        for index, cam in enumerate(self.cameras):
            cam_id = cam["id"]
            cam_url = cam["url_low"]
            cam_url_high = cam.get("url_high", "")

            viewer = existing_viewers.get(cam_id)
            if viewer:
                # Reconectar só se a URL mudou
                if viewer.current_url != cam_url:
                    viewer.set_url(cam_url)
                existing_viewers.pop(cam_id)  # Remove da lista de existentes
            else:
                # Criar novo viewer
                viewer = CameraViewer(cam_id, cam_url, cam_url_high)

            row = index // self.cols
            col = index % self.cols
            viewer.setAcceptDrops(True)
            self.layout.addWidget(viewer, row, col)
            self.viewers.append(viewer)
            self.original_positions[viewer] = (row, col)
            used_ids.add(cam_id)

        # Remove viewers que não estão mais em uso
        for cam_id, viewer in existing_viewers.items():
            viewer.close()
            self.layout.removeWidget(viewer)
            viewer.deleteLater()


if __name__ == "__main__":
    app = QApplication(sys.argv)

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

    window = MosaicoRTSP()
    window.showMaximized()

    splash.finish(window)  # fecha o splash depois que a janela abriu
    if QT_COMPAT_VERSION == 6:
        sys.exit(app.exec())

    else:
        sys.exit(app.exec_())
