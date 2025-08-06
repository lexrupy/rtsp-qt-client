import os
import subprocess
import time
import numpy as np
import cv2

from detect import detect_person
from qtcompat import QTimer, QImage, QImage_Format_RGB888, Qt_Compat_Qimage_ByteCount


ALARM_FILE = os.path.join(os.path.dirname(__file__), "doorbell.wav")
# ALARM_FILE = "/usr/share/sounds/freedesktop/stereo/alarm-clock-elapsed.oga"


def iniciar_monitoramento(
    viewers,
    intervalo_ms=2000,
    tempo_limite_travado=10,
    tempo_limite_escuro=10,
    brilho_minimo=20,
    similaridade_minima=0.999999,
):

    # Estrutura para armazenar estado externo
    estado = {}

    def inicializar_estado(v):
        estado[v] = {
            "last_frame_time": time.time(),
            "last_frame_img": None,
            "dark_start": None,
            "freeze_start": None,
        }

    def on_frame(viewer, qimage):
        agora = time.time()
        estado[viewer] = estado.get(viewer, {})
        estado[viewer]["last_frame_time"] = agora

        # Converte QImage para numpy array (RGBA)
        ptr = qimage.bits()
        ptr.setsize(Qt_Compat_Qimage_ByteCount(qimage))

        height = qimage.height()
        width = qimage.width()
        arr = np.array(ptr).reshape(height, width, 4 if qimage.hasAlphaChannel() else 3)

        # Garante formato RGB (OpenCV usa BGR por padrão)
        if arr.shape[2] == 4:
            arr = cv2.cvtColor(arr, cv2.COLOR_RGBA2RGB)
        else:
            arr = cv2.cvtColor(arr, cv2.COLOR_BGR2RGB)

        # ---- DETECÇÃO ----
        if viewer.detect_person:
            arr, person_detected = detect_person(arr)

            # Inicializa variáveis de controle se não existirem
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
                            subprocess.Popen(["paplay", ALARM_FILE])
            else:
                # Considera ausência se passou X segundos sem detecção
                if viewer.pessoa_presente and (
                    agora - viewer.ultimo_tempo_presenca > 3
                ):
                    viewer.pessoa_presente = False
                    viewer.alarme_tocado = False

        # w_rect = width
        # h_rect = height

        w_rect = 350
        h_rect = 60

        x_start = max(0, width - w_rect)
        y_start = 5
        x_end = width - 1
        y_end = h_rect - 1

        # Debug Rect
        # cv2.rectangle(arr, (x_start, y_start), (x_end, y_end), (0, 0, 255), 2)

        # Agora converte para QImage normalmente para exibir
        rgb_for_display = cv2.cvtColor(arr, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_for_display.shape
        bytesPerLine = ch * w
        qimg_debug = QImage(
            rgb_for_display.data, w, h, bytesPerLine, QImage_Format_RGB888
        ).copy()

        viewer.update_frame(qimg_debug)

        # Aqui para análise, recorte sem o retângulo original:
        cropped = arr[y_start : y_end + 1, x_start : x_end + 1]
        gray = cv2.cvtColor(cropped, cv2.COLOR_BGR2GRAY)
        small = cv2.resize(gray, (64, 36))

        estado[viewer]["last_frame_img"] = small

    # Conectar sinais frame_ready para cada viewer
    for v in viewers:
        v._frame_handler = lambda img, viewer=v: on_frame(viewer, img)
        v.thread.frame_ready.connect(v._frame_handler)
        inicializar_estado(v)

    def verificar():
        agora = time.time()
        for v in viewers:
            if v not in estado:
                inicializar_estado(v)
            est = estado[v]
            tempo_sem_frame = agora - est["last_frame_time"]
            if tempo_sem_frame > tempo_limite_travado:
                print(
                    f"[Monitor nofrm] Câmera {v.camera_id} travada (sem frame {tempo_sem_frame:.1f}s). Reconectando."
                )
                v.reconnect_with(force=True)
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
                    print(
                        f"[Monitor blk] Câmera {v.camera_id} com imagem escura persistente. Reconectando."
                    )
                    v.reconnect_with(force=True)
                    est["dark_start"] = None
                    est["freeze_start"] = None
                    est["last_frame_time"] = agora
                    continue
            else:
                est["dark_start"] = None

            # Verificar congelamento (frame repetido)
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

                if diff > similaridade_minima:
                    if est["freeze_start"] is None:
                        est["freeze_start"] = agora
                    elif agora - est["freeze_start"] > tempo_limite_travado:
                        print(
                            f"[Monitor sim] Câmera {v.camera_id} com imagem congelada. Reconectando."
                        )
                        v.reconnect_with(force=True)
                        est["freeze_start"] = None
                        est["dark_start"] = None
                        est["last_frame_time"] = agora
                else:
                    if similar < similaridade_minima / 2:
                        est["freeze_start"] = None

            est["prev_img"] = est["last_frame_img"]

    timer = QTimer()
    timer.timeout.connect(verificar)
    timer.start(intervalo_ms)
    return timer
