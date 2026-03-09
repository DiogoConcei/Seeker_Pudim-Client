import RPi.GPIO as GPIO
import time

# Usando a numeração BCM (lógica) do Raspberry Pi
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# --- Configuração dos Pinos ---
# Placa 1
P1_IN1 = 17
P1_IN2 = 27
P1_IN3 = 22
P1_IN4 = 23

# Placa 2
P2_IN1 = 24
P2_IN2 = 25
P2_IN3 = 5
P2_IN4 = 6

# Agrupando tudo para facilitar o setup
todos_pinos = [P1_IN1, P1_IN2, P1_IN3, P1_IN4, P2_IN1, P2_IN2, P2_IN3, P2_IN4]

# Define todos os pinos como SAÍDA e garante que comecem desligados (LOW)
GPIO.setup(todos_pinos, GPIO.OUT)
GPIO.output(todos_pinos, GPIO.LOW)


def testar_motor(nome, in_a, in_b):
    print(f"Testando {nome}...")
    GPIO.output(in_a, GPIO.HIGH)
    GPIO.output(in_b, GPIO.LOW)
    time.sleep(2)
    GPIO.output(in_a, GPIO.LOW)  # Desliga
    time.sleep(1)


try:
    print("Iniciando Teste 4x4 do Robô...\n")

    # Testando a Placa 1
    testar_motor("Placa 1 - Motor A (Verde/Amarelo)", P1_IN1, P1_IN2)
    testar_motor("Placa 1 - Motor B (Laranja/Vermelho)", P1_IN3, P1_IN4)

    # Testando a Placa 2
    testar_motor("Placa 2 - Motor A (Branco/Marrom)", P2_IN1, P2_IN2)
    testar_motor("Placa 2 - Motor B (Azul/Preto)", P2_IN3, P2_IN4)

    print("\nTeste individual concluído! Girando todas as rodas juntas por 2 segundos...")
    # Liga um lado de cada motor
    GPIO.output([P1_IN1, P1_IN3, P2_IN1, P2_IN3], GPIO.HIGH)
    time.sleep(2)

    # Desliga tudo
    GPIO.output(todos_pinos, GPIO.LOW)
    print("Sucesso!")

except KeyboardInterrupt:
    print("\nTeste interrompido.")

finally:
    # Limpa as portas para evitar de deixar motores ligados acidentalmente
    GPIO.cleanup()
    print("Pinos resetados.")