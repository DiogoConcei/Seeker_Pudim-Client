from dataclasses import dataclass

@dataclass
class ConfiguracaoCamera:
    largura: int = 640
    altura: int = 480
    fps: int = 15
    regiao_esquerda: float = 0.30
    regiao_direita: float = 0.70
    distancia_parada_cm: int = 50
