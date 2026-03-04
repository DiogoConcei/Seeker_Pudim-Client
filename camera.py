import cv2
from threading import Thread, Event


class CameraThread:
    def __init__(self, src=0, width=640, height=480, fps=15):
        self.cap = cv2.VideoCapture(src)

        # Limita resolução e FPS direto na câmera
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.cap.set(cv2.CAP_PROP_FPS, fps)
        # Reduz buffer interno: evita frames atrasados acumulados
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        self.ret, self.frame = self.cap.read()
        self.stopped = False
        self._frame_ready = Event()

    def start(self):
        Thread(target=self.update, args=(), daemon=True).start()
        return self

    def update(self):
        while not self.stopped:
            ret, frame = self.cap.read()
            if ret:
                self.ret, self.frame = ret, frame
                self._frame_ready.set()  # Sinaliza que há frame novo
            else:
                self.stopped = True

    def read(self):
        """Aguarda um frame novo antes de retornar (evita re-enviar frames duplicados)."""
        self._frame_ready.wait(timeout=1.0)
        self._frame_ready.clear()
        return self.ret, self.frame

    def release(self):
        self.stopped = True
        self.cap.release()