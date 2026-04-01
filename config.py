from dataclasses import dataclass

@dataclass
class ConfiguracaoCamera:
    largura: int = 640
    altura: int = 480
<<<<<<< HEAD
    regiao_esquerda: float = 0.10
    regiao_direita: float = 0.80
    distancia_parada_cm: int = 60
=======
    fps: int = 15
    regiao_esquerda: float = 0.30
    regiao_direita: float = 0.70
    distancia_parada_cm: int = 50
>>>>>>> feature/loc_p
