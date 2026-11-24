"""Inicialização do Airflow: cria o banco de metadados (separado, no mesmo Postgres), migra e cria o admin.

Lê as credenciais do ambiente (.env); não existe senha padrão. Idempotente: pode rodar de novo sem erro.
"""
import os
import subprocess
import sys
import time

import psycopg2
from psycopg2 import sql


def main() -> None:
    usuario = os.environ.get("AIRFLOW_ADMIN_USER", "")
    senha = os.environ.get("AIRFLOW_ADMIN_PASSWORD", "")
    if not usuario or not senha:
        sys.exit("Defina AIRFLOW_ADMIN_USER e AIRFLOW_ADMIN_PASSWORD no .env (sem senha padrão).")
    banco = os.environ["AIRFLOW_DB_NAME"]
    for tentativa in range(30):
        try:
            con = psycopg2.connect(host="postgres", user=os.environ["POSTGRES_USER"],
                                   password=os.environ["POSTGRES_PASSWORD"], dbname=os.environ["POSTGRES_DB"])
            break
        except psycopg2.OperationalError:
            time.sleep(2)
    else:
        sys.exit("Postgres não respondeu.")
    con.autocommit = True
    with con.cursor() as cur:
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (banco,))
        if cur.fetchone() is None:
            cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(banco)))
            print(f"banco {banco} criado")
    con.close()
    subprocess.run(["airflow", "db", "migrate"], check=True)
    existe = subprocess.run(["airflow", "users", "list"], capture_output=True, text=True, check=True).stdout
    if usuario not in existe.split():
        subprocess.run(["airflow", "users", "create", "--username", usuario, "--password", senha, "--firstname", "Admin",
                        "--lastname", "AnteceDengue", "--role", "Admin", "--email", "admin@antecedengue.local"],
                       check=True)
    print("airflow-init concluído")


if __name__ == "__main__":
    main()
