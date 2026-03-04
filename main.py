import asyncio
import json
import socket
import time

import cv2
import websockets
from zeroconf import Zeroconf, ServiceBrowser

try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False
    print("⚠️  RPi.GPIO não disponível — modo simulação ativo.")

from camera import CameraThread

# ── Pinos GPIO ────────────────────────────────────────────────────────────────
IN1, IN2 = 17, 27   # Motor esquerdo
IN3, IN4 = 22, 23   # Motor direito

if GPIO_AVAILABLE:
    GPIO.setmode(GPIO.BCM)
    GPIO.setup([IN1, IN2, IN3, IN4], GPIO.OUT)

# ── Configurações de streaming ────────────────────────────────────────────────
TARGET_FPS     = 15
FRAME_INTERVAL = 1.0 / TARGET_FPS
JPEG_QUALITY   = 60
ENCODE_PARAMS  = [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY]
MAX_TENTATIVAS = 3

# ── Configurações de seguimento ───────────────────────────────────────────────
ZONE_LEFT  = 0.35   # Centro da bbox < 35% da largura → virar esquerda
ZONE_RIGHT = 0.65   # Centro da bbox > 65% da largura → virar direita
CLASS_PESSOA = 0    # class_id da pessoa no YOLO
# ─────────────────────────────────────────────────────────────────────────────


# ── Controle dos motores ──────────────────────────────────────────────────────

def _set_motors(m_esq_frente, m_esq_tras, m_dir_frente, m_dir_tras):
    if not GPIO_AVAILABLE:
        return
    GPIO.output(IN1, m_esq_frente)
    GPIO.output(IN2, m_esq_tras)
    GPIO.output(IN3, m_dir_frente)
    GPIO.output(IN4, m_dir_tras)

def frente():
    print("▶ FRENTE")
    _set_motors(GPIO.HIGH, GPIO.LOW, GPIO.HIGH, GPIO.LOW)

def re():
    print("◀ RÉ")
    _set_motors(GPIO.LOW, GPIO.HIGH, GPIO.LOW, GPIO.HIGH)

def esquerda():
    """Gira no próprio eixo: motor dir frente, motor esq parado."""
    print("↰ ESQUERDA")
    _set_motors(GPIO.LOW, GPIO.LOW, GPIO.HIGH, GPIO.LOW)

def direita():
    """Gira no próprio eixo: motor esq frente, motor dir parado."""
    print("↱ DIREITA")
    _set_motors(GPIO.HIGH, GPIO.LOW, GPIO.LOW, GPIO.LOW)

def parar():
    print("■ PARAR")
    _set_motors(GPIO.LOW, GPIO.LOW, GPIO.LOW, GPIO.LOW)


# ── Lógica de seguimento ──────────────────────────────────────────────────────

def seguir_pessoa(detections: list, frame_width: int = 640):
    """
    Escolhe a detecção de pessoa com maior bounding box (mais próxima)
    e decide a direção com base na posição horizontal do centro.
    """
    pessoas = [d for d in detections if d["class_id"] == CLASS_PESSOA]

    if not pessoas:
        parar()
        return

    # Pega a pessoa com maior área (provavelmente a mais próxima)
    maior = max(pessoas, key=lambda d: (d["x2"] - d["x1"]) * (d["y2"] - d["y1"]))

    cx = (maior["x1"] + maior["x2"]) / 2          # Centro horizontal da bbox
    cx_norm = cx / frame_width                     # Normalizado entre 0.0 e 1.0

    if cx_norm < ZONE_LEFT:
        esquerda()
    elif cx_norm > ZONE_RIGHT:
        direita()
    else:
        frente()


# ── WebSocket ─────────────────────────────────────────────────────────────────

class WebcamListener:
    def __init__(self):
        self.found_uri = None

    def add_service(self, zc, type_, name):
        info = zc.get_service_info(type_, name)
        if info:
            address = socket.inet_ntoa(info.addresses[0])
            self.found_uri = f"ws://{address}:{info.port}/ws"

    def update_service(self, zc, type_, name): pass
    def remove_service(self, zc, type_, name): pass


async def buscar_servidor():
    zc = Zeroconf()
    listener = WebcamListener()
    browser = ServiceBrowser(zc, "_http._tcp.local.", listener)  # noqa: F841

    start = time.time()
    while not listener.found_uri and (time.time() - start) < 5:
        await asyncio.sleep(0.1)

    zc.close()
    return listener.found_uri


def handle_payload(payload: dict):
    frame_idx  = payload.get("frame")
    infer_ms   = payload.get("infer_time_ms", 0)
    detections = payload.get("detections", [])

    seguir_pessoa(detections)

    if detections:
        print(f"[Frame {frame_idx}] {len(detections)} detecção(ões) | {infer_ms:.1f}ms")


async def sender_loop(websocket, cam: CameraThread, stop_event: asyncio.Event):
    last_send = time.monotonic()

    while not cam.stopped and not stop_event.is_set():
        if not cam.has_new_frame():
            await asyncio.sleep(0.005)
            continue

        ret, frame = cam.read()
        if not ret:
            break

        elapsed = time.monotonic() - last_send
        if elapsed < FRAME_INTERVAL:
            await asyncio.sleep(FRAME_INTERVAL - elapsed)
            continue

        _, buffer = cv2.imencode('.jpg', frame, ENCODE_PARAMS)
        await websocket.send(buffer.tobytes())
        last_send = time.monotonic()

    stop_event.set()


async def receiver_loop(websocket, stop_event: asyncio.Event):
    while not stop_event.is_set():
        try:
            payload = json.loads(await websocket.recv())
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
                cam = CameraThread(src=0, width=640, height=480, fps=TARGET_FPS).start()
                print("🎥 Streaming iniciado!")

                stop_event = asyncio.Event()
                await asyncio.gather(
                    sender_loop(websocket, cam, stop_event),
                    receiver_loop(websocket, stop_event),
                )
                cam.release()

        except Exception as e:
            tentativas += 1
            print(f"⚠️ Conexão perdida: {e}. Tentando reconectar ({tentativas}/{MAX_TENTATIVAS})...")
            await asyncio.sleep(3)
        finally:
            parar()  # Garante que os motores param em qualquer falha


if __name__ == "__main__":
    try:
        asyncio.run(transmitir_video())
    except KeyboardInterrupt:
        print("\nCliente encerrado pelo usuário.")
    finally:
        parar()
        if GPIO_AVAILABLE:
            GPIO.cleanup()