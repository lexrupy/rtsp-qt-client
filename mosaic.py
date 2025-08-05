import os
import math
import time
import configparser

from qtcompat import (
    QLabel,
    QApplication,
    QSizePolicy_Expanding,
    QWidget,
    QGridLayout,
    QMessageBox,
    QMenu,
    QAction,
    QMessageBox_No,
    QMessageBox_Yes,
    QDialog_Accepted,
    Qt_AlignmentFlag_AlignCenter,
    Qt_Key_Escape,
    Qt_Key_F,
    Qt_Key_F11,
    Qt_KeyModifier_Control,
    QWIDGETSIZE_MAX,
)


from about import AboutDialog
from addcamera import AddCameraDialog
from cameraview import CameraViewer
from monitor import iniciar_monitoramento


CONFIG_FILE = os.path.expanduser("~/.config/rtsp-qt-client/config.ini")


class MosaicoRTSP(QWidget):
    def __init__(self):
        super().__init__()
        self.cameras = []
        self.config = configparser.ConfigParser()
        self.load_config()
        self.setMinimumSize(600, 408)
        self.setSizePolicy(QSizePolicy_Expanding, QSizePolicy_Expanding)
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
        self.monitor_timer = iniciar_monitoramento(self.viewers)

    def show_about_dialog(self):
        dlg = AboutDialog(self)
        dlg.exec()

    def add_camera_dialog(self):
        dlg = AddCameraDialog(self)
        if dlg.exec() == QDialog_Accepted:
            low_url = dlg.low_url
            high_url = dlg.high_url
            stream_type = dlg.stream_type
            detect_person = dlg.detect_person
            alarm_on_detect = dlg.alarm_on_detect
            self.add_camera_with_urls(
                low_url,
                high_url,
                stream_type=stream_type,
                detect_person=detect_person,
                alarm_on_detect=alarm_on_detect,
            )

    def copy_camera_dialog(self):
        if not self.selected_viewer:
            return

        cam_id = self.selected_viewer.camera_id
        cam_data = next((c for c in self.cameras if c["id"] == cam_id), None)
        if not cam_data:
            return

        dlg = AddCameraDialog(self, stream_type=cam_data["stream_type"])
        dlg.low_url_edit.setText(cam_data["url_low"])
        dlg.high_url_edit.setText(cam_data["url_high"])
        dlg.detect_checkbox.setChecked(cam_data.get("detect_person", False))
        dlg.alarm_checkbox.setChecked(cam_data.get("alarm_on_detect", False))

        if dlg.exec() == QDialog_Accepted:
            low_url = dlg.low_url
            high_url = dlg.high_url
            stream_type = dlg.stream_type
            detect_person = dlg.detect_person
            alarm_on_detect = dlg.alarm_on_detect
            self.add_camera_with_urls(
                low_url,
                high_url,
                stream_type=stream_type,
                detect_person=detect_person,
                alarm_on_detect=alarm_on_detect,
            )

    def edit_camera_dialog(self):
        if not self.selected_viewer:
            return
        viewer = self.selected_viewer
        cam_id = viewer.camera_id
        cam_data = next((c for c in self.cameras if c["id"] == cam_id), None)
        if not cam_data:
            return
        dlg = AddCameraDialog(self, stream_type=cam_data["stream_type"], editing=True)
        dlg.low_url_edit.setText(cam_data["url_low"])
        dlg.high_url_edit.setText(cam_data["url_high"])
        dlg.detect_checkbox.setChecked(cam_data.get("detect_person", False))
        dlg.alarm_checkbox.setChecked(cam_data.get("alarm_on_detect", False))
        if dlg.exec() == QDialog_Accepted:
            cam_data["url_low"] = dlg.low_url
            cam_data["url_high"] = dlg.high_url
            cam_data["stream_type"] = dlg.stream_type
            cam_data["detect_person"] = dlg.detect_person
            cam_data["alarm_on_detect"] = dlg.alarm_on_detect
            self.save_config()

            self.reload_cameras()

    def add_camera_with_urls(
        self,
        low_url,
        high_url,
        stream_type="Auto",
        detect_person=False,
        alarm_on_detect=False,
    ):
        # Acha um ID disponível para a nova câmera, ex: o próximo inteiro livre
        new_cam_id = max(cam["id"] for cam in self.cameras) + 1 if self.cameras else 1
        self.cameras.append(
            {
                "id": new_cam_id,
                "url_low": low_url,
                "url_high": high_url,
                "stream_type": stream_type,
                "detect_person": detect_person,
                "alarm_on_detect": alarm_on_detect,
            }
        )
        self.save_config()
        self.reload_cameras()

    def toggle_fullscreen(self, viewer):
        if not self.fullscreen_mode:
            self.original_positions = {
                v: self.layout.getItemPosition(self.layout.indexOf(v))[:2]
                for v in self.viewers
            }

            for v in self.viewers:
                if v != viewer:
                    v.hide()

            viewer.change_res(0)
            self.clear_layout()
            self.layout.addWidget(viewer, 0, 0, self.rows, self.cols)
            self.fullscreen_mode = True
            self.current_fullscreen = viewer

            viewer.show()
            viewer.update()

        else:
            self.setMaximumSize(self.size())
            viewer.change_res(1)
            self.clear_layout()

            for v in self.viewers:
                v.show()
                if v in self.original_positions:
                    r, c = self.original_positions[v]
                    self.layout.addWidget(v, r, c)
                v.update()

            self.layout.invalidate()
            self.layout.activate()
            self.updateGeometry()
            self.adjustSize()
            self.resize(self.sizeHint())

            self.fullscreen_mode = False
            self.current_fullscreen = None
            self.setMaximumSize(QWIDGETSIZE_MAX, QWIDGETSIZE_MAX)

    def clear_layout(self):
        while self.layout.count():
            item = self.layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                self.layout.removeWidget(widget)

    def swap_viewers(self, viewer1, viewer2):
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

        self.adjustSize()

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

    def closeEvent(self, event):
        for viewer in self.viewers:
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
        if not os.path.exists(CONFIG_FILE):
            return

        self.config.read(CONFIG_FILE)
        if "Cameras" not in self.config or "order" not in self.config["Cameras"]:
            return

        cameras_str = self.config["Cameras"]["order"]
        cam_ids = list(map(int, cameras_str.split(",")))

        for cam_id in cam_ids:
            section = f"Camera{cam_id}"
            if not self.config.has_section(section):
                continue  # Ignora se seção inexistente

            url_low = self.config.get(section, "url_low", fallback=None)
            url_high = self.config.get(section, "url_high", fallback=None)
            stream_type = self.config.get(section, "stream_type", fallback="GStreamer")
            detect_person = self.config.getboolean(
                section, "detect_person", fallback=False
            )
            alarm_on_detect = self.config.getboolean(
                section, "alarm_on_detect", fallback=False
            )

            if not url_low or not url_high:
                continue

            self.cameras.append(
                {
                    "id": cam_id,
                    "url_low": url_low,
                    "url_high": url_high,
                    "stream_type": stream_type,
                    "detect_person": detect_person,
                    "alarm_on_detect": alarm_on_detect,
                }
            )

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
            self.config.set(section, "stream_type", cam.get("stream_type", ""))
            self.config.set(section, "detect_person", str(cam.get("detect_person", "")))
            self.config.set(
                section, "alarm_on_detect", str(cam.get("alarm_on_detect", ""))
            )

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
        reconnect_action = QAction("Reconectar vídeos...", self)
        about_action = QAction("Sobre...", self)
        exit_action = QAction("Sair", self)
        exit_action.triggered.connect(self.do_exit)
        add_action.triggered.connect(self.add_camera_dialog)
        copy_action.triggered.connect(self.copy_camera_dialog)
        remove_action.triggered.connect(self.remove_camera_dialog)
        edit_action.triggered.connect(self.edit_camera_dialog)
        about_action.triggered.connect(self.show_about_dialog)
        reconnect_action.triggered.connect(self.reconnect_all_cameras)
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
        menu.addAction(reconnect_action)
        menu.addAction(about_action)
        menu.addAction(exit_action)
        menu.exec(event.globalPos())

    def reconnect_all_cameras(self):
        for viewer in self.viewers:
            viewer.reconnect_with(force=True)

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
            cam_url_high = cam["url_high"]
            stream_type = cam["stream_type"]
            detect_person = cam["detect_person"]
            alarm_on_detect = cam["alarm_on_detect"]

            viewer = existing_viewers.get(cam_id)

            if viewer:
                viewer.detect_person = detect_person
                viewer.alarm_on_detect = alarm_on_detect
                # Reconectar só se a URL mudou
                if viewer.current_url != cam_url:
                    viewer.reconnect_with(new_url=cam_url)

                existing_viewers.pop(cam_id)  # Remove da lista de existentes
            else:
                # Criar novo viewer
                viewer = CameraViewer(
                    cam_id,
                    cam_url,
                    cam_url_high,
                    stream_type,
                    detect_person,
                    alarm_on_detect,
                )

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
