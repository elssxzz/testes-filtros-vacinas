from pathlib import Path
import sqlite3
import ijson
import pandas as pd

pasta = Path(__file__).resolve().parent

pasta_saida = pasta / "resultados"
banco_dados = pasta_saida / "doses_fa_totais.db"

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
arquivos_json = sorted(pasta.glob("*.json"))
if not arquivos_json:
    raise SystemExit(f"Nenhum arquivo JSON encontrado em: {pasta}")

def processar_bloco(registros, conexao):
    dados = pd.DataFrame(registros)
    dados_fa = dados[dados["sg_imunobiologico"].str.contains("VFA", case=False, na=False)].reindex(columns=colunas)

    if not dados_fa.empty:
        datas = pd.to_datetime(dados_fa["dt_vacina"], errors="coerce", dayfirst=True)
        dados_fa = dados_fa.assign(mes=datas.dt.month, ano=datas.dt.year)
        linhas = dados_fa[["mes", "ano", "tp_sexo_paciente", "sg_uf_estabelecimento", "co_paciente"]]
        conexao.executemany(
            "INSERT INTO registros_fa (mes, ano, sexo, estado, co_paciente) VALUES (?, ?, ?, ?, ?)",
            linhas.itertuples(index=False, name=None),
        )

with sqlite3.connect(banco_dados) as conexao:
    conexao.execute("DROP TABLE IF EXISTS registros_fa")
    conexao.execute("DROP TABLE IF EXISTS doses_fa_totais")
    conexao.execute(
        """
        CREATE TABLE registros_fa (
            mes INTEGER,
            ano INTEGER,
            sexo TEXT,
            estado TEXT,
            co_paciente TEXT
        )
        """
    )
    conexao.execute(
        """
        CREATE TABLE doses_fa_totais (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mes INTEGER,
            ano INTEGER,
            doses_totais INTEGER NOT NULL,
            sexo TEXT,
            estado TEXT,
            mais_de_uma_dose INTEGER NOT NULL CHECK (mais_de_uma_dose IN (0, 1))
        )
        """
    )

    for arquivo in arquivos_json:
        print("Processando", arquivo.name)
        bloco = []

        with open(arquivo, "rb") as f:
            for registro in ijson.items(f, "item"):
                bloco.append(registro)
                if len(bloco) >= tamanho_bloco:
                    processar_bloco(bloco, conexao)
                    bloco = []

        if bloco:
            processar_bloco(bloco, conexao)

    conexao.execute(
        """
        WITH contagem_pacientes AS (
            SELECT co_paciente, COUNT(*) AS doses_paciente
            FROM registros_fa
            WHERE co_paciente IS NOT NULL AND TRIM(co_paciente) <> ''
            GROUP BY co_paciente
        ), registros_classificados AS (
            SELECT
                registros.mes,
                registros.ano,
                registros.sexo,
                registros.estado,
                CASE WHEN COALESCE(contagem_pacientes.doses_paciente, 1) > 1 THEN 1 ELSE 0 END AS mais_de_uma_dose
            FROM registros_fa AS registros
            LEFT JOIN contagem_pacientes USING (co_paciente)
        )
        INSERT INTO doses_fa_totais (mes, ano, doses_totais, sexo, estado, mais_de_uma_dose)
        SELECT
            registros_classificados.mes,
            registros_classificados.ano,
            COUNT(*),
            registros_classificados.sexo,
            registros_classificados.estado,
            registros_classificados.mais_de_uma_dose
        FROM registros_classificados
        GROUP BY
            registros_classificados.mes,
            registros_classificados.ano,
            registros_classificados.sexo,
            registros_classificados.estado,
            registros_classificados.mais_de_uma_dose
        """
    )
    conexao.execute("DROP TABLE registros_fa")

print(f"Banco de dados gerado: {banco_dados}")
