try:
    import RPi.GPIO as GPIO
except (ImportError, RuntimeError):
    # Mock para rodar no PC sem erro
    class GPIO_Mock:
        BCM = 'BCM'
        OUT = 'OUT'
        LOW = 0
        HIGH = 1
        def setmode(self, *args, **kwargs): pass
        def setwarnings(self, *args, **kwargs): pass
        def setup(self, *args, **kwargs): pass
        def output(self, *args, **kwargs): pass
        def cleanup(self, *args, **kwargs): pass
    GPIO = GPIO_Mock()

class ControleMotores:
    # Placa 1 — lado ESQUERDO
    _P1_IN1 = 5
    _P1_IN2 = 6
    _P1_IN3 = 12
    _P1_IN4 = 13

    # Placa 2 — lado DIREITO
    _P2_IN1 = 22
    _P2_IN2 = 23
    _P2_IN3 = 24
    _P2_IN4 = 25

    def __init__(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        self._pinos = [
            self._P1_IN1, self._P1_IN2, self._P1_IN3, self._P1_IN4,
            self._P2_IN1, self._P2_IN2, self._P2_IN3, self._P2_IN4
        ]

        GPIO.setup(self._pinos, GPIO.OUT)
        GPIO.output(self._pinos, GPIO.LOW)

    def _esquerda(self, frente: bool):
        in_a = GPIO.HIGH if frente else GPIO.LOW
        in_b = GPIO.LOW  if frente else GPIO.HIGH
        GPIO.output(self._P1_IN1, in_a)
        GPIO.output(self._P1_IN2, in_b)
        GPIO.output(self._P1_IN3, in_a)
        GPIO.output(self._P1_IN4, in_b)

    def _direita(self, frente: bool):
        in_a = GPIO.HIGH if frente else GPIO.LOW
        in_b = GPIO.LOW  if frente else GPIO.HIGH
        GPIO.output(self._P2_IN1, in_a)
        GPIO.output(self._P2_IN2, in_b)
        GPIO.output(self._P2_IN3, in_a)
        GPIO.output(self._P2_IN4, in_b)

    def frente(self):
        self._esquerda(frente=True)
        self._direita(frente=True)

    def re(self):
        self._esquerda(frente=False)
        self._direita(frente=False)

    def girar_esquerda(self):
        self._esquerda(frente=False)
        self._direita(frente=True)

    def girar_direita(self):
        self._esquerda(frente=True)
        self._direita(frente=False)

    def parar(self):
        GPIO.output(self._pinos, GPIO.LOW)

    def release(self):
        self.parar()
        GPIO.cleanup()