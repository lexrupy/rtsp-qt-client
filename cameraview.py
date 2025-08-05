from qtcompat import (
    QLabel,
    QPixmap,
    QApplication,
    QDrag,
    QTimer,
    QMimeData,
    QSizePolicy_Expanding,
    Qt_AlignmentFlag_AlignCenter,
    Qt_AspectRatioMode_KeepAspectRatio,
    Qt_TransformationMode_SmoothTransformation,
    Qt_LeftButton,
    Qt_MoveAction,
    Qt_Compat_GetMousePoint,
)

from camera import CameraThread


class CameraViewer(QLabel):
    def __init__(self, camera, url_low=None, url_high=None, stream_type="Auto"):
        super().__init__()
        self.camera_id = camera
        self.url_low = url_low if url_low else ""
        self.url_high = url_high if url_high else ""
        self.stream_type = stream_type
        self.reconnecting = False
        self.setScaledContents(True)
        self.setMinimumSize(0, 0)
        self.setAlignment(Qt_AlignmentFlag_AlignCenter)
        self.setSizePolicy(QSizePolicy_Expanding, QSizePolicy_Expanding)
        self.setText("Conectando...")
        self.setStyleSheet("background-color: black; color: white; font-size: 16px;")
        self.last_esc_time = 0
        self.thread = None
        self.current_url = self.url_low
        self.connecting = False
        self.init_capture()

    def init_capture(self):
        self.connecting = True
        self.setPixmap(QPixmap())  # limpa imagem antiga
        self.thread = CameraThread(self.current_url, self.stream_type)
        self.thread.frame_ready.connect(self.update_frame)
        self.thread.connection_failed.connect(self.show_connection_error)
        self.thread.start()

    def change_res(self, res=0):
        new_url = self.url_high if res == 0 else self.url_low
        self.reconnect_with(new_url=new_url)

    def reconnect_with(self, new_url=None, force=False):
        new_url = new_url or self.current_url

        if not force and new_url == self.current_url:
            return  # Nada mudou

        self.current_url = new_url

        if self.thread:
            self.thread.restart_with(new_url, force=force)
        else:
            self.init_capture()

    def update_frame(self, img):
        if self.connecting:
            self.connecting = False
            self.setText("")  # esconde texto conectando
        self.setPixmap(
            QPixmap.fromImage(img).scaled(
                self.size(),
                Qt_AspectRatioMode_KeepAspectRatio,
                Qt_TransformationMode_SmoothTransformation,
            )
        )

    def show_connection_error(self):
        self.connecting = False
        self.setText("Erro ao conectar")
        self.setPixmap(QPixmap())  # limpa imagem

    def close(self):
        if self.thread:
            self.thread.stop()
            self.thread.wait()
            self.thread = None
        super().close()

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

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update()
        self.updateGeometry()
