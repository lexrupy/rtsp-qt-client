import time
from qtcompat import (
    QLabel,
    QPixmap,
    QApplication,
    QDrag,
    QMimeData,
    QWidget,
    QPushButton,
    QVBoxLayout,
    QSizePolicy_Expanding,
    Qt_AlignmentFlag_AlignCenter,
    Qt_AspectRatioMode_KeepAspectRatio,
    Qt_TransformationMode_FastTransformation,
    Qt_LeftButton,
    Qt_MoveAction,
    Qt_Compat_GetMousePoint,
)

from camera import CameraThread, READ_TIMEOUT_MSEC


THREAD_STOP_TIMEOUT = READ_TIMEOUT_MSEC + 5000


class CameraViewer(QLabel):
    def __init__(
        self,
        camera,
        url_low=None,
        url_high=None,
        stream_type="Auto",
        detect_person=False,
        alarm_on_detect=False,
        alarm_type="doorbell"
    ):
        super().__init__()
        self.camera_id = camera
        self.url_low = url_low if url_low else ""
        self.url_high = url_high if url_high else ""
        self.stream_type = stream_type
        self.detect_person = detect_person
        self.alarm_on_detect = alarm_on_detect
        self.reconnecting = False
        self._ultimo_frame_ts = None
        self.setScaledContents(True)
        self.setMinimumSize(0, 0)
        self.setAlignment(Qt_AlignmentFlag_AlignCenter)
        self.setSizePolicy(QSizePolicy_Expanding, QSizePolicy_Expanding)
        self.setText("Conectando...")
        self.setStyleSheet("background-color: black; color: white; font-size: 16px;")
        self.last_esc_time = time.time()
        self.pessoa_presente = False
        self.ultimo_tempo_presenca = time.time()
        self.alarme_tocado = False
        self.thread = None
        self.alarm_type = alarm_type
        self.current_url = self.url_low
        self.connecting = False
        self.disabled = False
        self._overlay = None
        self.init_capture()

    def _create_overlay(self):
        ov = QWidget(self)
        ov.setStyleSheet(
            "background-color: rgba(30,30,30,200); color: white; font-size: 14px;"
        )
        lay = QVBoxLayout(ov)
        lay.addStretch(1)
        lbl = QLabel("")
        lbl.setAlignment(Qt_AlignmentFlag_AlignCenter)
        lay.addWidget(lbl)
        btn_desativar = QPushButton("Desativar")
        btn_reconectar = QPushButton("Reconectar")
        btn_desativar.setStyleSheet(
            "background-color: #c0392b; color: white; padding: 6px; border-radius: 4px;"
        )
        btn_reconectar.setStyleSheet(
            "background-color: #2980b9; color: white; padding: 6px; border-radius: 4px;"
        )
        btn_desativar.clicked.connect(lambda: self.set_disabled(True))
        btn_reconectar.clicked.connect(self._on_reconectar)
        lay.addWidget(btn_desativar, alignment=Qt_AlignmentFlag_AlignCenter)
        lay.addWidget(btn_reconectar, alignment=Qt_AlignmentFlag_AlignCenter)
        lay.addStretch(1)
        ov.hide()
        return ov

    def set_problem(self, motivo):
        if self.disabled:
            return
        if self._overlay is None:
            self._overlay = self._create_overlay()
        self._overlay.findChild(QLabel).setText(f"Câmera {motivo}")
        self._overlay.setGeometry(0, 0, self.width(), self.height())
        self._overlay.show()
        self._overlay.raise_()

    def clear_problem(self):
        if self._overlay is not None:
            self._overlay.hide()

    def _on_reconectar(self):
        self.clear_problem()
        self.reconnect_with(force=True)
        parent = self.parent()
        if hasattr(parent, 'on_camera_retomar'):
            parent.on_camera_retomar(self.camera_id)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._overlay is not None:
            self._overlay.setGeometry(0, 0, self.width(), self.height())

    def init_capture(self):
        self.connecting = True
        self.setPixmap(QPixmap())
        self.thread = CameraThread(self.current_url, self.stream_type)
        self.thread.connection_failed.connect(self.show_connection_error)
        self._reconnect_monitor()
        self.thread.start()

    def _reconnect_monitor(self):
        if hasattr(self, '_frame_handler') and self._frame_handler is not None:
            self.thread.frame_ready.connect(self._frame_handler)
        else:
            self.thread.frame_ready.connect(self.update_frame)

    def _disconnect_thread(self, thread):
        try:
            if hasattr(self, '_frame_handler') and self._frame_handler is not None:
                thread.frame_ready.disconnect(self._frame_handler)
            else:
                thread.frame_ready.disconnect(self.update_frame)
            thread.connection_failed.disconnect(self.show_connection_error)
        except TypeError:
            pass

    def change_res(self, res=0):
        new_url = self.url_high if res == 0 else self.url_low
        self.reconnect_with(new_url=new_url)

    def reconnect_with(self, new_url=None, force=False):
        new_url = new_url or self.current_url

        if not force and new_url == self.current_url:
            return

        self.current_url = new_url

        if self.thread:
            self._replace_thread()
        else:
            self.init_capture()

    def _replace_thread(self):
        old_thread = self.thread
        self._disconnect_thread(old_thread)
        old_thread.stop()

        pending = getattr(self, "_pending_threads", None)
        if pending is None:
            self._pending_threads = []
        self._pending_threads.append(old_thread)

        def _cleanup(th):
            th.deleteLater()
            pending = getattr(self, "_pending_threads", None)
            if pending is not None and th in pending:
                pending.remove(th)

        old_thread.finished.connect(lambda: _cleanup(old_thread))
        # Se a thread ja terminou (morreu por connection_failed antes do
        # reconnect, por exemplo), o sinal finished nao vai mais disparar.
        # Limpa agora para nao acumular threads presas em _pending_threads.
        if old_thread.isFinished():
            _cleanup(old_thread)

        self.thread = CameraThread(self.current_url, self.stream_type)
        self.thread.connection_failed.connect(self.show_connection_error)
        self._reconnect_monitor()
        self.thread.start()

    def update_frame(self, img):
        if self.disabled:
            return
        self._ultimo_frame_ts = time.time()
        if self.connecting:
            self.connecting = False
            self.setText("")
        self.setPixmap(
            QPixmap.fromImage(img).scaled(
                self.size(),
                Qt_AspectRatioMode_KeepAspectRatio,
                Qt_TransformationMode_FastTransformation,
            )
        )

    def show_connection_error(self):
        if self.disabled:
            return
        self.connecting = False
        self.setText("Erro ao conectar")
        self.setPixmap(QPixmap())

    def set_disabled(self, state):
        self.disabled = state
        if state:
            self.clear_problem()
            if self.thread:
                self._disconnect_thread(self.thread)
                self.thread.stop()
                if not self.thread.wait(THREAD_STOP_TIMEOUT):
                    print(
                        f"[Camera {self.camera_id}] Thread travada ao desativar"
                    )
                self.thread = None
            self.setScaledContents(False)
            self.clear()
            self.setText("Desativada")
            self.setStyleSheet(
                "background-color: #333; color: white; font-size: 20px; font-weight: bold;"
            )
        else:
            self.clear_problem()
            self.setScaledContents(True)
            self.setText("Conectando...")
            self.setStyleSheet(
                "background-color: black; color: white; font-size: 16px;"
            )
            self.current_url = self.url_low
            self.init_capture()
        parent = self.parent()
        if hasattr(parent, 'on_camera_disabled'):
            parent.on_camera_disabled(self.camera_id, state)
        if not state and hasattr(parent, 'on_camera_retomar'):
            parent.on_camera_retomar(self.camera_id)

    def close(self):
        pending = getattr(self, "_pending_threads", [])
        for th in pending:
            th.stop()
        if self.thread:
            self._disconnect_thread(self.thread)
            self.thread.stop()
            if not self.thread.wait(THREAD_STOP_TIMEOUT):
                print(
                    f"[Camera {self.camera_id}] Thread travada no close, abandonando..."
                )
            self.thread = None
        super().close()

    def mouseDoubleClickEvent(self, event):
        if not self.disabled:
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
            pix = self.grab()
            thumb = pix.scaled(
                200, 150,
                Qt_AspectRatioMode_KeepAspectRatio,
                Qt_TransformationMode_FastTransformation,
            )
            drag.setPixmap(thumb)
            drag.setHotSpot(thumb.rect().center())
            drag.exec(Qt_MoveAction)
