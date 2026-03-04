import cv2
from threading import Thread, Lock


class CameraThread:
    def __init__(self, src=0, width=640, height=480, fps=15):
        self.cap = cv2.VideoCapture(src)

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.cap.set(cv2.CAP_PROP_FPS, fps)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        self.ret, self.frame = self.cap.read()
        self.stopped = False
        self._lock = Lock()          # Protege acesso concorrente ao frame
        self._new_frame = False      # Flag: indica se há frame novo não enviado

    def start(self):
        Thread(target=self.update, args=(), daemon=True).start()
        return self

    def update(self):
        while not self.stopped:
            ret, frame = self.cap.read()
            if ret:
                with self._lock:
                    # Sobrescreve sempre — o transmissor pega o mais recente
                    self.ret, self.frame = ret, frame
                    self._new_frame = True
            else:
                self.stopped = True

    def read(self):
        """Retorna o frame mais recente disponível, sem esperar."""
        with self._lock:
            self._new_frame = False
            return self.ret, self.frame

    def has_new_frame(self):
        """Verifica se há um frame novo desde o último read()."""
        return self._new_frame

    def release(self):
        self.stopped = True
        self.cap.release()