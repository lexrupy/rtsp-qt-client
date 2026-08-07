import cv2
import time

from qtcompat import (
    QImage,
    QThread,
    pyqtSignal,
    QImage_Format_RGB888,
)


READ_TIMEOUT_MSEC = 3000


class CameraThread(QThread):
    frame_ready = pyqtSignal(QImage)
    connection_failed = pyqtSignal()
    stopped = pyqtSignal()

    def __init__(self, url, stream_type="Auto"):
        super().__init__()
        self.url = url
        self.stream_type = stream_type
        self.running = True
        self.cap = None

    def run(self):
        self.cap = self.configure_cap()

        if self.cap is None or not self.cap.isOpened():
            self.connection_failed.emit()
            self.stopped.emit()
            return

            read_falhas = 0
        max_falhas = 4
        fps_limit = 25
        min_interval = 1.0 / fps_limit
        last_emit = 0.0
        while self.running:
            if self.cap is None or not self.cap.isOpened():
                break
            ret, frame = self.cap.read()
            if self.cap is None or not self.running:
                break
            if not ret:
                # Blip transitorio de rede: nao desiste na primeira falha.
                # read()/timeout ja bloqueou; tenta mais umas vezes antes de
                # declarar perda de conexao.
                read_falhas += 1
                if read_falhas >= max_falhas:
                    self.connection_failed.emit()
                    break
                continue
            read_falhas = 0
            # Limita a emissao p/ nao afogar a event loop da UI quando a
            # camera glitcha e entrega frames mais rapido que o normal.
            agora = time.time()
            if agora - last_emit < min_interval:
                continue
            last_emit = agora
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb.shape
            bytesPerLine = ch * w
            image = QImage(rgb.data, w, h, bytesPerLine, QImage_Format_RGB888).copy()
            self.frame_ready.emit(image)

        self._release_cap()
        self.stopped.emit()

    def configure_cap(self):
        try:
            if self.stream_type == "GStreamer":
                gst = (
                    f"rtspsrc location={self.url} latency=0 ! "
                    "rtph264depay ! avdec_h264 ! videoconvert ! "
                    "appsink sync=false drop=true max-buffers=1"
                )
                cap = cv2.VideoCapture(gst, cv2.CAP_GSTREAMER)
            elif self.stream_type == "OpenCV":
                cap = cv2.VideoCapture(self.url)
            elif self.stream_type == "Ffmpeg":
                cap = cv2.VideoCapture(self.url, cv2.CAP_FFMPEG)
            elif self.stream_type == "DirectShow":
                cap = cv2.VideoCapture(self.url, cv2.CAP_DSHOW)
            elif self.stream_type == "MSMF":
                cap = cv2.VideoCapture(self.url, cv2.CAP_MSMF)
            else:
                cap = cv2.VideoCapture(self.url)

            self._apply_cap_timeout(cap)
            return cap
        except Exception as e:
            print(f"[Camera] Erro ao configurar cap: {e}")
            return None

    def _apply_cap_timeout(self, cap):
        try:
            cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, READ_TIMEOUT_MSEC)
        except Exception:
            pass
        try:
            cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, READ_TIMEOUT_MSEC)
        except Exception:
            pass

    def stop(self):
        self.running = False
        # Se read() estiver preso, liberar a cap desbloqueia a thread
        cap = self.cap
        if cap is not None:
            try:
                cap.release()
            except Exception:
                pass

    def _release_cap(self):
        if self.cap is not None:
            try:
                if self.cap.isOpened():
                    self.cap.release()
            except Exception:
                pass
            finally:
                self.cap = None
