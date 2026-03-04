import asyncio
import socket
import time

import cv2
import websockets
from zeroconf import Zeroconf, ServiceBrowser

from camera import CameraThread

# ── Configurações centralizadas ──────────────────────────────────────────────
TARGET_FPS = 15                      # FPS alvo para o streaming
FRAME_INTERVAL = 1.0 / TARGET_FPS   # Intervalo entre frames (~66ms para 15 FPS)
JPEG_QUALITY = 60                    # Qualidade JPEG (0-100); 60 é bom custo-benefício
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
                cam = CameraThread(src=0, width=640, height=480, fps=TARGET_FPS).start()
                print("🎥 Streaming iniciado! Pressione 'q' no servidor para encerrar.")

                last_send = time.monotonic()

                while not cam.stopped:
                    # Se não há frame novo, cede o controle e tenta de novo
                    if not cam.has_new_frame():
                        await asyncio.sleep(0.005)
                        continue

                    ret, frame = cam.read()  # Pega o mais recente (nunca frame antigo)

                    if not ret:
                        break

                    # Controle de FPS: se chegou cedo demais, volta ao loop
                    # (pode haver frame mais novo disponível no próximo ciclo)
                    now = time.monotonic()
                    elapsed = now - last_send
                    if elapsed < FRAME_INTERVAL:
                        await asyncio.sleep(FRAME_INTERVAL - elapsed)
                        continue

                    _, buffer = cv2.imencode('.jpg', frame, ENCODE_PARAMS)
                    await websocket.send(buffer.tobytes())
                    last_send = time.monotonic()

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