import asyncio
import json
import socket
import time

import cv2
import websockets
from zeroconf import Zeroconf, ServiceBrowser

from camera import CameraThread
from config import ConfiguracaoCamera
from motores import ControleMotores

# ── Configurações centralizadas ──────────────────────────────────────────────
FRAME_INTERVAL = 1.0 / 15
JPEG_QUALITY = 60
ENCODE_PARAMS = [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY]
MAX_TENTATIVAS = 3


# ─────────────────────────────────────────────────────────────────────────────


async def sender_loop(websocket, cam: CameraThread, stop_event: asyncio.Event):
    last_send = time.monotonic()

    while not cam.stopped and not stop_event.is_set():
        if not cam.has_new_frame():
            await asyncio.sleep(0.005)
            continue

        ret, frame = cam.read()
        if not ret:
            break

        now = time.monotonic()
        elapsed = now - last_send
        if elapsed < FRAME_INTERVAL:
            await asyncio.sleep(FRAME_INTERVAL - elapsed)
            continue

        _, buffer = cv2.imencode('.jpg', frame, ENCODE_PARAMS)
        await websocket.send(buffer.tobytes())
        last_send = time.monotonic()

    stop_event.set()


class WebcamListener:
    def __init__(self, config: ConfiguracaoCamera, motores: ControleMotores):
        self.found_uri = None
        self.config = config
        self.motores = motores
        self.target_track_id = -1

    def handle_payload(self, payload: dict):
        detections = payload.get("detections", [])
        if not detections:
            self.motores.parar()
            self.target_track_id = -1
            return

        # Tenta encontrar o alvo atual ou escolhe o maior (mais próximo)
        target = None
        if self.target_track_id != -1:
            target = next((d for d in detections if d["track_id"] == self.target_track_id), None)
        
        if target is None:
            # Escolhe o objeto com a maior altura (mais confiável para proximidade)
            target = max(detections, key=lambda b: b["y2"] - b["y1"])
            self.target_track_id = target["track_id"]

        distancia = self.medir_distancia(target)
        velocidade = target.get("speed", 0)
        self._agir(distancia, velocidade)

    def medir_distancia(self, target):
        x1 = target["x1"]
        distancia_cm = target.get("dist_m", 999)

        if x1 < self.config.largura * self.config.regiao_esquerda:
            return 0  # Esquerda
        if x1 > self.config.largura * self.config.regiao_direita:
            return -2 # Direita
        
        return int(distancia_cm)

    def _agir(self, distancia: int, velocidade: float):
        if distancia == 0:
            print(f"🔄 GIRAR ESQUERDA | Alvo: {self.target_track_id}")
            self.motores.girar_esquerda()
        elif distancia == -2:
            print(f"🔄 GIRAR DIREITA | Alvo: {self.target_track_id}")
            self.motores.girar_direita()
        elif distancia <= self.config.distancia_parada_cm:
            print(f"🛑 PARAR | Dist: {distancia}cm <= {self.config.distancia_parada_cm}cm")
            self.motores.parar()
        else:
            print(f"🚀 FRENTE | Dist: {distancia}cm | Vel: {velocidade}")
            self.motores.frente()

    async def receiver_loop(self, websocket, stop_event: asyncio.Event):
        while not stop_event.is_set():
            try:
                message = await websocket.recv()
                payload = json.loads(message)
                self.handle_payload(payload)
            except Exception:
                stop_event.set()
                break

    def add_service(self, zc, type_, name):
        info = zc.get_service_info(type_, name)
        if info:
            address = socket.inet_ntoa(info.addresses[0])
            port = info.port
            self.found_uri = f"ws://{address}:{port}/ws"

    def update_service(self, zc, type_, name):
        pass

    def remove_service(self, zc, type_, name):
        pass


async def buscar_servidor(listener: WebcamListener):
    listener.found_uri = None
    zc = Zeroconf()
    browser = ServiceBrowser(zc, "_http._tcp.local.", listener)  # noqa: F841

    start_time = time.time()
    while not listener.found_uri and (time.time() - start_time) < 5:
        await asyncio.sleep(0.1)

    zc.close()
    return listener.found_uri


async def transmitir_video():
    tentativas = 0
    config = ConfiguracaoCamera()
    motores = ControleMotores()
    listener = WebcamListener(config, motores)

    while tentativas < MAX_TENTATIVAS:
        uri = await buscar_servidor(listener)
        if not uri:
            tentativas += 1
            await asyncio.sleep(2)
            continue

        try:
            async with websockets.connect(uri) as websocket:
                tentativas = 0
                cam = CameraThread(
                    src=0,
                    width=config.largura,
                    height=config.altura,
                    fps=config.fps
                ).start()
                stop_event = asyncio.Event()

                try:
                    await asyncio.gather(
                        sender_loop(websocket, cam, stop_event),
                        listener.receiver_loop(websocket, stop_event),
                    )
                finally:
                    cam.release()

        except Exception as e:
            tentativas += 1
            print(f"⚠️ Erro: {e}")
            await asyncio.sleep(3)

    motores.release()


if __name__ == "__main__":
    try:
        asyncio.run(transmitir_video())
    except KeyboardInterrupt:
        print("\nCliente encerrado pelo usuário.")