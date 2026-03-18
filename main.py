import asyncio
import json
import socket
import time

import cv2
import websockets
from zeroconf import Zeroconf, ServiceBrowser

from camera import CameraThread

# ── Configurações centralizadas ──────────────────────────────────────────────
TARGET_FPS = 15
FRAME_INTERVAL = 1.0 / TARGET_FPS
JPEG_QUALITY = 60
ENCODE_PARAMS = [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY]
MAX_TENTATIVAS = 3


# ─────────────────────────────────────────────────────────────────────────────


class WebcamListener:
    def __init__(self):
        self.found_uri = None

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


async def buscar_servidor():
    zc = Zeroconf()
    listener = WebcamListener()
    browser = ServiceBrowser(zc, "_http._tcp.local.", listener)  # noqa: F841

    start_time = time.time()
    while not listener.found_uri and (time.time() - start_time) < 5:
        await asyncio.sleep(0.1)

    zc.close()
    return listener.found_uri


def handle_payload(payload: dict):
    """
    Chamado a cada resposta do servidor.
    Personalize aqui o que fazer com as detecções.
    """
    frame_idx = payload.get("frame")
    infer_ms = payload.get("infer_time_ms", 0)
    detections = payload.get("detections", [])

    if detections:
        print(f"[Frame {frame_idx}] {len(detections)} detecção(ões) | {infer_ms:.1f}ms")
        for det in detections:
            print(f"{payload["detections"]}")


async def sender_loop(websocket, cam: CameraThread, stop_event: asyncio.Event):
    """Captura frames da câmera e envia ao servidor."""
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


async def receiver_loop(websocket, stop_event: asyncio.Event):
    """Recebe payloads JSON do servidor e os processa."""
    while not stop_event.is_set():
        try:
            message = await websocket.recv()
            payload = json.loads(message)
            handle_payload(payload)
        except Exception:
            stop_event.set()
            break


async def transmitir_video():
    tentativas = 0

    while tentativas < MAX_TENTATIVAS:
        uri = await buscar_servidor()

        if not uri:
            tentativas += 1
            print(f"📡 Servidor não encontrado. Tentativa {tentativas}/{MAX_TENTATIVAS}")
            await asyncio.sleep(2)
            continue

        try:
            print(f"🔗 Conectando ao servidor em: {uri}")
            async with websockets.connect(uri) as websocket:
                tentativas = 0
<<<<<<< HEAD
                cam = CameraThread(
                    src=0,
                    width=config.largura,
                    height=config.altura,
                    fps=TARGET_FPS
                ).start()
=======
                cam = CameraThread(src=0, width=640, height=480, fps=TARGET_FPS).start()
                print("🎥 Streaming iniciado!")

>>>>>>> 844441210d223ac97af29cd58ecc035a52a44185
                stop_event = asyncio.Event()

                # Envia frames e recebe payloads em paralelo
                await asyncio.gather(
                    sender_loop(websocket, cam, stop_event),
                    receiver_loop(websocket, stop_event),
                )

                cam.release()

        except Exception as e:
            tentativas += 1
            print(f"⚠️ Conexão perdida: {e}. Tentando reconectar ({tentativas}/{MAX_TENTATIVAS})...")
            await asyncio.sleep(3)


if __name__ == "__main__":
    try:
        asyncio.run(transmitir_video())
    except KeyboardInterrupt:
        print("\nCliente encerrado pelo usuário.")
