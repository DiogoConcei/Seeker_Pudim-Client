import cv2
import asyncio
import websockets

async def stream():
    uri = "ws://localhost:8000/ws"  # Endereço do seu servidor FastAPI
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