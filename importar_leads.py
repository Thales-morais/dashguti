"""
Script de importação única: lê o CSV exportado do Google Sheets
e insere todos os leads na tabela lead_guti_trampah do Supabase.

Uso:
    pip install pandas supabase python-dotenv
    python importar_leads.py leads.csv
"""

import sys
import os
import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
TABLE = "lead_guti_trampah"
BATCH_SIZE = 500

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal",
}


def parse_date(value):
    if pd.isna(value) or str(value).strip() == "":
        return None
    s = str(value).strip()
    # tenta ISO primeiro (2026-03-31T02:33:25)
    for fmt in (
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y",
        "%Y-%m-%d",
    ):
        try:
            return pd.to_datetime(s, format=fmt).isoformat()
        except (ValueError, TypeError):
            continue
    # última tentativa genérica
    try:
        return pd.to_datetime(s, dayfirst=True).isoformat()
    except Exception:
        return None


def insert_batch(records: list):
    url = f"{SUPABASE_URL}/rest/v1/{TABLE}"
    resp = requests.post(url, headers=HEADERS, json=records, timeout=30)
    if resp.status_code not in (200, 201):
        raise RuntimeError(f"Erro ao inserir: {resp.status_code} — {resp.text}")


def main(csv_path: str):
    print(f"Lendo {csv_path}...")
    df = pd.read_csv(csv_path)

    # normaliza cabeçalhos: strip + uppercase
    df.columns = [c.strip().upper() for c in df.columns]

    # renomeia para os nomes da tabela (uppercase conforme criado)
    col_map = {
        "DATA": "DATA",
        "NOME": "NOME",
        "EMAIL": "EMAIL",
        "TELEFONE": "TELEFONE",
        "FONTE": "FONTE",
    }
    df = df.rename(columns=col_map)

    # mantém só as colunas que existem na tabela
    cols_existentes = [c for c in col_map.values() if c in df.columns]
    df = df[cols_existentes]

    # corrige coluna DATA
    if "DATA" in df.columns:
        df["DATA"] = df["DATA"].apply(parse_date)

    # TELEFONE como string sem decimais
    if "TELEFONE" in df.columns:
        df["TELEFONE"] = (
            df["TELEFONE"]
            .apply(lambda x: str(int(float(x))) if pd.notna(x) and str(x).strip() != "" else None)
        )

    # substitui NaN por None
    df = df.where(pd.notnull(df), None)

    records = df.to_dict("records")
    total = len(records)
    print(f"Total de registros: {total}")

    for i in range(0, total, BATCH_SIZE):
        batch = records[i : i + BATCH_SIZE]
        insert_batch(batch)
        print(f"  Inserido {min(i + BATCH_SIZE, total)}/{total}")

    print("Importação concluída!")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python importar_leads.py <caminho_do_csv>")
        sys.exit(1)
    main(sys.argv[1])
