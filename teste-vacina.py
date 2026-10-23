from pathlib import Path
import ijson
import pandas as pd

pasta = Path(__file__).resolve().parent

pasta_saida = pasta / "resultados"

tamanho_bloco = 50000   

colunas = [
    "tp_sexo_paciente",
    "co_vacina_grupo_atendimento",
    "co_estrategia_vacinacao",
    "sg_uf_estabelecimento",
    "dt_vacina",
    "co_paciente"
]

if not pasta.is_dir():
    raise SystemExit(f"Diretório não encontrado: {pasta}")

pasta_saida.mkdir(parents=True, exist_ok=True)
arq_final = pasta_saida / "consolidado_febre_amarela.csv"
arq_final.unlink(missing_ok=True)

resumo = []

def processar_bloco(registros):
    dados = pd.DataFrame(registros)
    dados_fa = dados[dados["sg_imunobiologico"].str.contains("VFA", case=False, na=False)]
    dados_fa = dados_fa.reindex(columns=colunas)

    if len(dados_fa) > 0:
        ja_existe = arq_final.exists()
        dados_fa.to_csv(arq_final, index=False, mode="a", header=not ja_existe)

    return len(dados), len(dados_fa)


for arquivo in sorted(pasta.glob("*.json")):
    print("Processando", arquivo.name)
    total = 0
    febre_amarela = 0
    bloco = []

    with open(arquivo, "rb") as f:
        for registro in ijson.items(f, "item"):
            bloco.append(registro)
            if len(bloco) >= tamanho_bloco:
                t, fa = processar_bloco(bloco)
                total += t
                febre_amarela += fa
                bloco = []

    if bloco:
        t, fa = processar_bloco(bloco)
        total += t
        febre_amarela += fa

    resumo.append({"arquivo": arquivo.name, "total_doses": total, "doses_febre_amarela": febre_amarela})
    print(f"  Total: {total:,} | Febre Amarela: {febre_amarela:,}")

resumo = pd.DataFrame(resumo)

print()
print(f"Total de doses no programa: {resumo['total_doses'].sum():,}")
print(f"Total de doses de Febre Amarela: {resumo['doses_febre_amarela'].sum():,}")
print(f"Arquivo gerado: {arq_final}")
