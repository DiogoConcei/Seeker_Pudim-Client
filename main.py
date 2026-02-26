import asyncio
import socket
import time

import cv2
import websockets
from zeroconf import Zeroconf, ServiceBrowser


class Listener:
    def __init__(self):
        self.found_address = None

    def add_service(self, zc, type_, name):
        info = zc.get_service_info(type_, name)

        if info:
            address = socket.inet_ntoa(info.addresses[0])
            print(f"Servidor encontrado: {address}:{info.port}")
            self.found_address = f"ws://{address}:{info.port}/ws"

        # Adicione este método para resolver o aviso:
    def update_service(self, zc, type_, name):
        # Por enquanto não precisamos fazer nada aqui
        pass

    def remove_service(self, zc, type_, name):
        # É boa prática ter este também, caso o servidor caia
        pass


zeroconf = Zeroconf()
listener = Listener()
browser = ServiceBrowser(zeroconf, "_http._tcp.local.", listener)

while not listener.found_address:
    time.sleep(0.1)

# Endereço do seu servidor FastAPI
uri = listener.found_address


async def stream():
    async with websockets.connect(uri) as websocket:
        cap = cv2.VideoCapture(0)

        while True:
            ret, frame = cap.read()
            if not ret: break

            # Codifica como JPG
            _, buffer = cv2.imencode('.jpg', frame)

            # Converte o buffer para bytes e envia
            await websocket.send(buffer.tobytes())

            # Pequena pausa para não atropelar o processador
            await asyncio.sleep(0.01)

        cap.release()


asyncio.run(stream())
