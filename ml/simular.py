"""Gera registros sintéticos compatíveis com os instantes dos fluxos de agenda e fila."""
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent


def gerar(destino=RAIZ / "atendimentos.csv"):
    rng = np.random.default_rng(2633898)
    linhas = []
    for indice, dia in enumerate(pd.bdate_range("2026-01-05", periods=135)):
        for bloco, hora in enumerate((8, 10, 13, 15)):
            demanda = int(rng.integers(2, 11) + (bloco == 1) + (indice >= 103))
            capacidade = int(rng.integers(5, 10))
            pendentes = max(0, int(rng.poisson(1.2 + bloco * .4)) - 1)
            chegadas = []
            for ordem in range(demanda):
                tipo = rng.choice(["primeira", "retorno", "encaixe"], p=[.32,.52,.16])
                antecedencia = 0 if tipo == "encaixe" else int(rng.integers(1, 26))
                faltas_previas = int(rng.choice([0, 1, 2, 3], p=[.63,.23,.10,.04]))
                turno = "manhã" if hora < 12 else "tarde"
                escore = -2.9 + .63 * faltas_previas + .07 * antecedencia + .45 * (turno == "tarde") + .4 * (tipo == "primeira")
                prob = 1 / (1 + np.exp(-escore))
                falta = int(rng.random() < prob)
                chegada = None if falta else round(max(0, pendentes * 2 + 1.55 * ordem +
                    17 * (ordem + pendentes >= capacidade) + rng.normal(2, 5)), 1)
                fila = None if falta else pendentes + max(0, ordem - capacidade // 2)
                chegadas.append((tipo, antecedencia, faltas_previas, turno, falta, chegada, fila))
            presentes = sum(1 - item[4] for item in chegadas)
            lotacao = int(presentes + pendentes > capacidade)
            bloco_inicio = dia + pd.Timedelta(hours=hora)
            for tipo, antecedencia, faltas_previas, turno, falta, espera, fila in chegadas:
                linhas.append({"bloco_inicio": bloco_inicio, "tipo": tipo, "turno": turno,
                    "dia_semana": dia.day_name(), "antecedencia_dias": antecedencia,
                    "faltas_previas": faltas_previas if rng.random() > .06 else None,
                    "fila_chegada": fila, "marcacoes_bloco": demanda,
                    "pendentes_inicio": pendentes, "capacidade_bloco": capacidade,
                    "no_show": falta, "espera_min": espera, "lotacao": lotacao})
    pd.DataFrame(linhas).to_csv(destino, index=False)


if __name__ == "__main__":
    gerar()
