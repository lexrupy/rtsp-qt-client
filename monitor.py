import os
import subprocess
import time
import numpy as np
import cv2

from detect import detect_person
from qtcompat import QTimer, QImage, QImage_Format_RGB888, Qt_Compat_Qimage_ByteCount


ALARM_FILE = os.path.join(os.path.dirname(__file__), "alarm.wav")
DOORBEL_FILE = os.path.join(os.path.dirname(__file__), "doorbell.wav")

MAX_RETRIES = 3


def iniciar_monitoramento(
    viewers,
    intervalo_ms=2000,
    tempo_limite_travado=10,
    tempo_limite_escuro=10,
    brilho_minimo=20,
    similaridade_minima=0.999999,
):

    estado = {}

    def inicializar_estado(v):
        estado[v] = {
            "last_frame_time": time.time(),
            "last_frame_img": None,
            "dark_start": None,
            "freeze_start": None,
            "retry_count": 0,
        }

    def _thumbnail_from_qimage(qimage):
        ptr = qimage.bits()
        ptr.setsize(Qt_Compat_Qimage_ByteCount(qimage))
        height = qimage.height()
        width = qimage.width()
        arr = np.array(ptr).reshape(
            height, width, 4 if qimage.hasAlphaChannel() else 3
        )
        if arr.shape[2] == 4:
            arr = cv2.cvtColor(arr, cv2.COLOR_RGBA2RGB)
        gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
        return cv2.resize(gray, (64, 36))

    def on_frame(viewer, qimage):
        agora = time.time()
        est = estado.setdefault(viewer, {})
        est["last_frame_time"] = agora
        if getattr(viewer, "disabled", False):
            return

        if viewer.detect_person:
            ptr = qimage.bits()
            ptr.setsize(Qt_Compat_Qimage_ByteCount(qimage))
            height = qimage.height()
            width = qimage.width()
            arr = np.array(ptr).reshape(
                height, width, 4 if qimage.hasAlphaChannel() else 3
            )

            if arr.shape[2] == 4:
                arr = cv2.cvtColor(arr, cv2.COLOR_RGBA2RGB)
            else:
                arr = cv2.cvtColor(arr, cv2.COLOR_BGR2RGB)

            arr, person_detected = detect_person(arr)

            if not hasattr(viewer, "pessoa_presente"):
                viewer.pessoa_presente = False
                viewer.ultimo_tempo_presenca = 0
                viewer.alarme_tocado = False

            if person_detected:
                viewer.ultimo_tempo_presenca = agora
                if not viewer.pessoa_presente:
                    viewer.pessoa_presente = True
                    if not viewer.alarme_tocado:
                        viewer.alarme_tocado = True
                        viewer.last_detection_time = agora
                        if viewer.alarm_on_detect:
                            if viewer.alarm_type == "doorbell":
                                subprocess.Popen(["paplay", DOORBEL_FILE])
                            else:
                                subprocess.Popen(["paplay", ALARM_FILE])
            else:
                if viewer.pessoa_presente and (
                    agora - viewer.ultimo_tempo_presenca > 3
                ):
                    viewer.pessoa_presente = False
                    viewer.alarme_tocado = False

            gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
            est["last_frame_img"] = cv2.resize(gray, (64, 36))

            rgb_display = cv2.cvtColor(arr, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_display.shape
            qimg_display = QImage(
                rgb_display.data, w, h, ch * w, QImage_Format_RGB888
            ).copy()
            viewer.update_frame(qimg_display)
        else:
            viewer.update_frame(qimage)

            last_thumb = est.get("_thumb_time", 0)
            if est["last_frame_img"] is None or (agora - last_thumb) >= 2:
                est["last_frame_img"] = _thumbnail_from_qimage(qimage)
                est["_thumb_time"] = agora

    def conectar_viewer(v):
        inicializar_estado(v)
        v._frame_handler = lambda img, viewer=v: on_frame(viewer, img)
        if not getattr(v, "disabled", False) and v.thread is not None:
            v.thread.frame_ready.connect(v._frame_handler)

    for v in viewers:
        conectar_viewer(v)

    def _reconnect_or_disable(v, motivo):
        est = estado[v]
        est["retry_count"] = est.get("retry_count", 0) + 1
        if est["retry_count"] >= MAX_RETRIES:
            print(
                f"[Monitor] Câmera {v.camera_id} desativada após {MAX_RETRIES} tentativas ({motivo})"
            )
            v.set_disabled(True)
        else:
            print(
                f"[Monitor {motivo}] Câmera {v.camera_id} (tentativa {est['retry_count']}/{MAX_RETRIES}). Reconectando."
            )
            v.reconnect_with(force=True)
            est["prev_img"] = None

    def verificar():
        agora = time.time()
        for v in viewers:
            if getattr(v, "disabled", False):
                continue

            if v not in estado:
                inicializar_estado(v)
            est = estado[v]

            tempo_sem_frame = agora - est["last_frame_time"]
            if tempo_sem_frame > tempo_limite_travado:
                _reconnect_or_disable(v, "nofrm")
                est["last_frame_time"] = agora
                est["dark_start"] = None
                est["freeze_start"] = None
                continue

            if est["last_frame_img"] is None:
                continue

            brilho = np.mean(est["last_frame_img"])
            if brilho < brilho_minimo:
                if est["dark_start"] is None:
                    est["dark_start"] = agora
                elif agora - est["dark_start"] > tempo_limite_escuro:
                    _reconnect_or_disable(v, "blk")
                    est["dark_start"] = None
                    est["freeze_start"] = None
                    est["last_frame_time"] = agora
                    continue
            else:
                est["dark_start"] = None

            last_img = est.get("prev_img")
            if last_img is not None:
                diff = (
                    np.mean(
                        np.abs(
                            est["last_frame_img"].astype(float) - last_img.astype(float)
                        )
                    )
                    / 255
                )
                similar = 1 - diff

                if similar > similaridade_minima:
                    if est["freeze_start"] is None:
                        est["freeze_start"] = agora
                    elif agora - est["freeze_start"] > tempo_limite_travado:
                        _reconnect_or_disable(v, "sim")
                        est["freeze_start"] = None
                        est["dark_start"] = None
                        est["last_frame_time"] = agora
                else:
                    est["freeze_start"] = None

            # Só zera retry_count se TUDO estiver normal
            if est.get("dark_start") is None and est.get("freeze_start") is None:
                est["retry_count"] = 0

            est["prev_img"] = est["last_frame_img"]

    timer = QTimer()
    timer.timeout.connect(verificar)
    timer.start(intervalo_ms)
    return timer, conectar_viewer
