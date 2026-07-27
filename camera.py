import cv2

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

        while self.running:
            if self.cap is None or not self.cap.isOpened():
                break
            ret, frame = self.cap.read()
            if not ret or not self.running:
                if self.running:
                    self.connection_failed.emit()
                break
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
                    "rtph264depay ! avdec_h264 ! videoconvert ! appsink sync=false"
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

    def _release_cap(self):
        if self.cap is not None:
            try:
                if self.cap.isOpened():
                    self.cap.release()
            except Exception:
                pass
            finally:
                self.cap = None
