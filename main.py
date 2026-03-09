import RPi.GPIO as GPIO
import time

# Configuração para usar a numeração BCM (nomes lógicos dos GPIOs)
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# Pinos que você definiu
IN1, IN2 = 17, 27
IN3, IN4 = 22, 23

# Configurando os pinos como saída de energia (OUTPUT)
GPIO.setup([IN1, IN2, IN3, IN4], GPIO.OUT)

# Garantindo que tudo comece desligado
GPIO.output([IN1, IN2, IN3, IN4], GPIO.LOW)

try:
    print("Testando Motor 1 (Pinos 17 e 27)...")
    # Para girar, um pino precisa ser HIGH (energia) e o outro LOW (sem energia)
    GPIO.output(IN1, GPIO.HIGH)
    GPIO.output(IN2, GPIO.LOW)
    time.sleep(2)  # Mantém girando por 2 segundos

    # Para o motor 1
    GPIO.output(IN1, GPIO.LOW)
    print("Motor 1 parado.")
    time.sleep(1)

    print("Testando Motor 2 (Pinos 22 e 23)...")
    GPIO.output(IN3, GPIO.HIGH)
    GPIO.output(IN4, GPIO.LOW)
    time.sleep(2)  # Mantém girando por 2 segundos

    # Para o motor 2
    GPIO.output(IN3, GPIO.LOW)
    print("Motor 2 parado.")

    print("Teste finalizado com sucesso!")

except KeyboardInterrupt:
    print("\nTeste interrompido pelo usuário.")

finally:
    # Limpa as configurações das portas GPIO para evitar problemas no próximo uso
    GPIO.cleanup()