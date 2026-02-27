import cv2
from threading import Thread

class CameraThread:
    def __init__(self, src=0):
        self.cap = cv2.VideoCapture(src)
        self.ret, self.frame = self.cap.read()
        self.stopped = False

    def start(self):
        Thread(target=self.update, args=(), daemon=True).start()
        return self

    def update(self):
        while not self.stopped:
            ret, frame = self.cap.read()
            if ret:
                self.ret, self.frame = ret, frame
            else:
                self.stopped = True

    def read(self):
        return self.ret, self.frame

    def release(self):
        self.stopped = True
        self.cap.release()