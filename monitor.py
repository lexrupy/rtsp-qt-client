import os
import subprocess
import time
import numpy as np
import cv2

from detect import detect_person
from qtcompat import QTimer, QImage, QImage_Format_RGB888, Qt_Compat_Qimage_ByteCount


ALARM_FILE = os.path.join(os.path.dirname(__file__), "alarm.wav")
DOORBEL_FILE = os.path.join(os.path.dirname(__file__), "doorbell.wav")

def iniciar_monitoramento(
    viewers,
    intervalo_ms=1000,
    tempo_limite_travado=10,
    tempo_limite_escuro=10,
    tempo_limite_sem_imagem=20,
    brilho_minimo=20,
    similaridade_minima=0.999999,
    intervalo_reconexao=20,
):

    estado = {}

    def inicializar_estado(v):
        estado[v] = {
            "last_frame_time": time.time(),
            "last_frame_img": None,
            "dark_start": None,
            "freeze_start": None,
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

            if getattr(viewer, "detect_person", False):
                arr, person_detected = detect_person(arr)
            else:
                person_detected = False

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
            try:
                v.thread.frame_ready.disconnect(v.update_frame)
            except TypeError:
                pass
            v.thread.frame_ready.connect(v._frame_handler)

    for v in viewers:
        conectar_viewer(v)

    def _sugerir_problema(v, motivo):
        est = estado[v]
        est["em_sugestao"] = True
        est["dark_start"] = None
        est["freeze_start"] = None
        est["_flag_time"] = time.time()
        if hasattr(v, "set_problem"):
            v.set_problem(motivo)

    def _auto_reconectar(v):
        if hasattr(v, "_on_reconectar"):
            v._on_reconectar()

    def verificar():
        agora = time.time()
        for v in viewers:
            if getattr(v, "disabled", False):
                continue

            if v not in estado:
                inicializar_estado(v)
            est = estado[v]

            if est.get("em_sugestao"):
                # Reconecta automaticamente (com intervalo) enquanto a
                # camera estiver com problema; nao desativa nem pisca.
                if (agora - est.get("_flag_time", agora)) >= intervalo_reconexao:
                    est["_flag_time"] = agora
                    _auto_reconectar(v)
                continue

            tempo_sem_frame = agora - est["last_frame_time"]
            if tempo_sem_frame > tempo_limite_sem_imagem:
                _sugerir_problema(v, "sem imagem")
                continue

            if est["last_frame_img"] is None:
                continue

            # Pula analise se o thumbnail nao mudou desde a ultima checagem
            if est.get("_checked_img") is est["last_frame_img"]:
                continue
            est["_checked_img"] = est["last_frame_img"]

            brilho = np.mean(est["last_frame_img"])
            if brilho < brilho_minimo:
                if est["dark_start"] is None:
                    est["dark_start"] = agora
                elif agora - est["dark_start"] > tempo_limite_escuro:
                    _sugerir_problema(v, "escura")
                    continue
            else:
                est["dark_start"] = None

            last_img = est.get("prev_img")
            if last_img is not None:
                diff = np.mean(cv2.absdiff(est["last_frame_img"], last_img)) / 255
                similar = 1 - diff

                if similar > similaridade_minima:
                    if est["freeze_start"] is None:
                        est["freeze_start"] = agora
                    elif agora - est["freeze_start"] > tempo_limite_travado:
                        _sugerir_problema(v, "travada")
                        continue
                else:
                    est["freeze_start"] = None

            est["prev_img"] = est["last_frame_img"]

    def descartar_viewer(v):
        estado.pop(v, None)

    def retomar_viewer(v):
        est = estado.get(v)
        if est:
            est.pop("em_sugestao", None)
            est["dark_start"] = None
            est["freeze_start"] = None
            est["last_frame_time"] = time.time()
        if hasattr(v, "clear_problem"):
            v.clear_problem()

    timer = QTimer()
    timer.timeout.connect(verificar)
    timer.start(intervalo_ms)
    return timer, conectar_viewer, descartar_viewer, retomar_viewer
