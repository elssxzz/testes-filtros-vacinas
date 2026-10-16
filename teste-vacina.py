import pandas as pd
import ijson

arquivo = "vacinacao_mai_2025.json"
arq_saida = "vacinas_febre_amarela_mai.csv"
div = 30000

colunas_saida = [
    "tp_sexo_paciente",
    "co_vacina_grupo_atendimento",
    "co_estrategia_vacinacao",
    "sg_uf_estabelecimento",
]

def processar_bloco(registros, primeiro_bloco):
    dados = pd.DataFrame(registros)
    dados_fa = dados[dados["sg_imunobiologico"].str.contains("VFA", case=False, na=False)]

    if len(dados_fa) > 0:
        dados_fa = dados_fa.reindex(columns=colunas_saida)
        dados_fa.to_csv(
            arq_saida,
            index=False,
            mode="w" if primeiro_bloco else "a",
            header=primeiro_bloco,
        )
        primeiro_bloco = False

    return len(dados), len(dados_fa), primeiro_bloco

total_geral = 0
casos_totais = 0
primeiro_bloco = True
bloco_atual = []

with open(arquivo, "rb") as f:
    for registro in ijson.items(f, "item"):
        bloco_atual.append(registro)

        if len(bloco_atual) >= div:
            n_total, n_fa, primeiro_bloco = processar_bloco(bloco_atual, primeiro_bloco)
            total_geral += n_total
            casos_totais += n_fa
            bloco_atual = []

if bloco_atual:
    n_total, n_fa, primeiro_bloco = processar_bloco(bloco_atual, primeiro_bloco)
    total_geral += n_total
    casos_totais += n_fa

print(f"Total de doses aplicadas no programa de imunização: {total_geral:,}")
print(f"Total de doses para Febre Amarela: {casos_totais:,}")
