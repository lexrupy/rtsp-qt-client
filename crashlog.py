import os
import sys
import faulthandler
import threading
import traceback
from datetime import datetime


LOG_DIR = os.path.expanduser("~/.config/rtsp-qt-client")
LOG_FILE = os.path.join(LOG_DIR, "crash.log")


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _write(msg):
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        with open(LOG_FILE, "a") as f:
            f.write(msg + "\n")
    except Exception:
        pass


def _excepthook(exc_type, exc_value, exc_tb):
    tb = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    _write(f"[{_now()}] EXCEPTION (main)\n{tb}")
    try:
        sys.__excepthook__(exc_type, exc_value, exc_tb)
    except Exception:
        pass


def _thread_excepthook(args):
    tb = "".join(traceback.format_exception(
        args.exc_type, args.exc_value, args.exc_traceback
    ))
    _write(f"[{_now()}] EXCEPTION (thread {args.thread.name})\n{tb}")


def _faulthandler_setup():
    os.makedirs(LOG_DIR, exist_ok=True)
    try:
        f = open(LOG_FILE, "a")
        faulthandler.enable(f)
    except Exception:
        pass


def setup_crash_logging():
    _write(f"[{_now()}] ===== iniciou aplicacao pid={os.getpid()} =====")
    sys.excepthook = _excepthook
    if hasattr(threading, "excepthook"):
        threading.excepthook = _thread_excepthook
    _faulthandler_setup()