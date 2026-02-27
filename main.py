import asyncio
import socket
import time

import cv2
import websockets
from zeroconf import Zeroconf, ServiceBrowser

from camera import CameraThread


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
    # Não funciona sem essa linha
    browser = ServiceBrowser(zc, "_http._tcp.local.", listener)

    start_time = time.time()
    while not listener.found_uri and (time.time() - start_time) < 5:
        await asyncio.sleep(0.1)

    zc.close()  # Fecha o radar após a busca
    return listener.found_uri


async def transmitir_video():
    tentativas = 0
    max_tentativas = 3

    while tentativas < max_tentativas:
        uri = await buscar_servidor()

        if not uri:
            tentativas += 1
            print(f"📡 Servidor não encontrado. Tentativa {tentativas}/{max_tentativas}")
            await asyncio.sleep(2)
            continue

        try:
            print(f"🔗 Conectando ao servidor em: {uri}")
            async with websockets.connect(uri) as websocket:
                tentativas = 0

                cam = CameraThread(0).start()

                print("🎥 Streaming iniciado! Pressione 'q' no servidor para encerrar.")

                while not cam.stopped:
                    ret, frame = cam.read()

                    if not ret: break

                    _, buffer = cv2.imencode('.jpg', frame)
                    await websocket.send(buffer.tobytes())

                    await asyncio.sleep(0.01)

                cam.release()
        except Exception as e:
            tentativas += 1
            print(f"⚠️ Conexão perdida: {e}. Tentando reconectar ({tentativas}/{max_tentativas})...")
            await asyncio.sleep(3)


if __name__ == "__main__":
    try:
        asyncio.run(transmitir_video())
    except KeyboardInterrupt:
        print("\nCliente encerrado pelo usuário.")
