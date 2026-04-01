# Configuração Seeker Pudim: ESP32-CAM + ESP32 Motores

Este guia contém a adaptação do código original (Python/OpenCV) para MicroPython, separando as funções de visão computacional e controle físico em dois microcontroladores.

---

## 1. ESP32-CAM (Transmissor de Vídeo)
**Função:** Captura frames da câmera e envia via WebSocket para o servidor (PC) processar.

```python
import camera
import time
import network
import uwebsockets.client as websocket

# --- CONFIGURAÇÕES ---
SSID = "SuaRedeWiFi"
PASSWORD = "SuaSenhaWiFi"
WS_URI = "ws://192.168.1.XXX:8000/ws" # IP do seu computador (Servidor)

def conectar_wifi():
    sta_if = network.WLAN(network.STA_IF)
    if not sta_if.isconnected():
        print('Conectando ao WiFi...')
        sta_if.active(True)
        sta_if.connect(SSID, PASSWORD)
        while not sta_if.isconnected():
            time.sleep(0.5)
    print('WiFi conectado:', sta_if.ifconfig()[0])

def iniciar_camera():
    # Configuração para ESP32-CAM AI-Thinker
    camera.init(0, format=camera.JPEG, framesize=camera.FRAME_VGA)
    camera.quality(12) # Qualidade JPEG (10-63)
    print("Câmera inicializada.")

def main():
    conectar_wifi()
    iniciar_camera()
    
    while True:
        try:
            print("Conectando ao servidor WebSocket...")
            ws = websocket.connect(WS_URI)
            print("Conectado!")
            
            while True:
                buf = camera.capture()
                if buf:
                    ws.send(buf)
                # Ajuste o sleep para controlar o FPS e não sobrecarregar o WiFi
                time.sleep_ms(40) 
                
        except Exception as e:
            print("Erro no loop da câmera:", e)
            time.sleep(2)

if __name__ == "__main__":
    main()
```

---

## 2. ESP32 Standard (Controlador de Motores)
**Função:** Conecta-se ao servidor, recebe as coordenadas de detecção (JSON) e aciona as Pontes H.

```python
import machine
import json
import time
import network
import uwebsockets.client as websocket

# --- CONFIGURAÇÕES DE PINOS (GPIO) ---
# Altere os números conforme sua ligação física no ESP32
P1_IN1 = machine.Pin(17, machine.Pin.OUT)
P1_IN2 = machine.Pin(27, machine.Pin.OUT)
P1_IN3 = machine.Pin(22, machine.Pin.OUT)
P1_IN4 = machine.Pin(23, machine.Pin.OUT)

P2_IN1 = machine.Pin(24, machine.Pin.OUT)
P2_IN2 = machine.Pin(25, machine.Pin.OUT)
P2_IN3 = machine.Pin(32, machine.Pin.OUT) # Nota: Pinos 5/6 podem variar no ESP32
P2_IN4 = machine.Pin(33, machine.Pin.OUT)

TODOS_PINOS = [P1_IN1, P1_IN2, P1_IN3, P1_IN4, P2_IN1, P2_IN2, P2_IN3, P2_IN4]

# --- PARÂMETROS DE NAVEGAÇÃO ---
DEADZONE = 50
DIST_PARADA = 30 # cm
SSID = "SuaRedeWiFi"
PASSWORD = "SuaSenhaWiFi"
WS_URI = "ws://192.168.1.XXX:8000/ws"

def parar():
    for p in TODOS_PINOS: p.value(0)

def frente():
    P1_IN1.value(1); P1_IN2.value(0); P1_IN3.value(1); P1_IN4.value(0)
    P2_IN1.value(1); P2_IN2.value(0); P2_IN3.value(1); P2_IN4.value(0)

def girar_esquerda():
    P1_IN1.value(0); P1_IN2.value(1); P1_IN3.value(0); P1_IN4.value(1)
    P2_IN1.value(1); P2_IN2.value(0); P2_IN3.value(1); P2_IN4.value(0)

def girar_direita():
    P1_IN1.value(1); P1_IN2.value(0); P1_IN3.value(1); P1_IN4.value(0)
    P2_IN1.value(0); P2_IN2.value(1); P2_IN3.value(0); P2_IN4.value(1)

def conectar_wifi():
    sta_if = network.WLAN(network.STA_IF)
    sta_if.active(True)
    sta_if.connect(SSID, PASSWORD)
    while not sta_if.isconnected(): time.sleep(0.5)
    print("WiFi Motores OK:", sta_if.ifconfig()[0])

def processar_comando(msg):
    try:
        data = json.loads(msg)
        detections = data.get("detections", [])
        
        if not detections:
            parar()
            return

        # Lógica original: foca no maior objeto
        target = max(detections, key=lambda b: b["y2"] - b["y1"])
        erro_x = target.get("erro_x", 0)
        dist_cm = target.get("dist_cm", 999)

        if erro_x < -DEADZONE:
            girar_esquerda()
        elif erro_x > DEADZONE:
            girar_direita()
        elif dist_cm <= DIST_PARADA:
            parar()
        else:
            frente()
            
    except Exception as e:
        print("Erro ao processar JSON:", e)
        parar()

def main():
    conectar_wifi()
    parar()
    
    while True:
        try:
            ws = websocket.connect(WS_URI)
            while True:
                msg = ws.recv()
                if msg:
                    processar_comando(msg)
        except Exception:
            parar()
            time.sleep(2)

if __name__ == "__main__":
    main()
```

---

## 3. Requisitos de Instalação

1. **Firmware MicroPython**: 
   - No ESP32-CAM, use um firmware que já inclua suporte ao módulo `camera` (ex: [lemariva/micropython-camera-driver](https://github.com/lemariva/micropython-camera-driver)).
2. **Biblioteca WebSocket**:
   - Instale a `uwebsockets` em ambos os ESP32. Você pode subir os arquivos `client.py` e `protocol.py` usando ferramentas como **Thonny** ou **mpremote**.
3. **Servidor (PC)**:
   - Certifique-se de que o seu servidor (que roda o OpenCV e o WebSocket) esteja escutando no IP correto e na porta configurada nos scripts acima.

## 4. Dicas de Hardware
- **Alimentação**: O ESP32-CAM consome picos de corrente ao transmitir WiFi. Use uma fonte externa de 5V estável. **Não alimente apenas pelo USB do PC** se o vídeo estiver caindo.
- **Pinos**: No ESP32-CAM, evite usar os pinos GPIO 0, 2, 4, 12, 13, 14, 15 se estiver usando o cartão SD ou a câmera, pois eles são compartilhados.
- **GND Comum**: Lembre-se de conectar o GND do ESP32, do ESP32-CAM e das Pontes H (bateria) todos juntos.
