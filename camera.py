import cv2

from qtcompat import (
    QImage,
    QThread,
    pyqtSignal,
    QImage_Format_RGB888,
)


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

        if not self.cap.isOpened():
            self.connection_failed.emit()
            self.stopped.emit()
            return

        while self.running:
            if self.cap is None or not self.cap.isOpened():
                break
            ret, frame = self.cap.read()
            if not ret:
                self.connection_failed.emit()
                break
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb.shape
            bytesPerLine = ch * w
            image = QImage(rgb.data, w, h, bytesPerLine, QImage_Format_RGB888).copy()
            self.frame_ready.emit(image)

        self.cap.release()
        self.stopped.emit()

    def configure_cap(self):
        if self.stream_type == "GStreamer":
            gst = (
                f"rtspsrc location={self.url} latency=0 ! "
                "rtph264depay ! avdec_h264 ! videoconvert ! appsink sync=false"
            )
            return cv2.VideoCapture(gst, cv2.CAP_GSTREAMER)
        if self.stream_type == "OpenCV":
            return cv2.VideoCapture(self.url)
        if self.stream_type == "Ffmpeg":
            return cv2.VideoCapture(self.url, cv2.CAP_FFMPEG)
        if self.stream_type == "DirectShow":
            return cv2.VideoCapture(self.url, cv2.CAP_DSHOW)
        if self.stream_type == "MSMF":
            return cv2.VideoCapture(self.url, cv2.CAP_MSMF)
        return cv2.VideoCapture(self.url)

    def restart_with(self, url, force=False):
        if not force and url == self.url:
            return

        self.stop()
        if self.isRunning():
            self.wait()

        self.url = url
        self.running = True
        self.start()

    def stop(self):
        self.running = False
        try:
            if hasattr(self, "cap") and self.cap.isOpened():
                self.cap.release()
                self.cap = None

        except Exception:
            pass
