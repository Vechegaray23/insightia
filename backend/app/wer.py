from collections import defaultdict
from datetime import date
from typing import List

DATASET: List[str] = [
    "hola, gracias por llamar",
    "buenos dias, en que puedo ayudarte",
    "este es un ejemplo de frase",
    "la inteligencia artificial avanza rapidamente",
    "python es un lenguaje muy versatil",
    "la lluvia en sevilla es una pura maravilla",
    "hoy es un buen dia para aprender",
    "los unicornios no existen pero son divertidos",
    "la prueba de audio debe ser clara",
    "las montanas son altas y majestuosas",
    "el cafe de la manana es esencial",
    "la musica relaja la mente y el alma",
    "leer libros abre la puerta al conocimiento",
    "nunca dejes de explorar el mundo",
    "el sol brilla intensamente en verano",
    "las estrellas iluminan la noche",
    "la tecnologia cambia nuestras vidas",
    "programar es crear soluciones",
    "cada dia trae nuevas oportunidades",
    "la practica hace al maestro",
]


def wer(reference: str, hypothesis: str) -> float:
    """Calculate word error rate between two phrases."""
    r = reference.split()
    h = hypothesis.split()
    d = [[0] * (len(h) + 1) for _ in range(len(r) + 1)]
    for i in range(len(r) + 1):
        d[i][0] = i
    for j in range(len(h) + 1):
        d[0][j] = j
    for i in range(1, len(r) + 1):
        for j in range(1, len(h) + 1):
            cost = 0 if r[i - 1] == h[j - 1] else 1
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + cost)
    return d[-1][-1] / float(len(r)) if r else 0.0


class DailyWER:
    def __init__(self) -> None:
        self.data = defaultdict(list)

    def add(self, score: float) -> None:
        self.data[date.today().isoformat()].append(score)

    def metrics(self) -> dict:
        return {
            day: sum(vals) / len(vals) if vals else 0.0 for day, vals in self.data.items()
        }


metrics = DailyWER()

