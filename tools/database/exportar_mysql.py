"""Genera un respaldo SQL de la base indicada por MYSQL_PUBLIC_URL o DATABASE_URL."""

import argparse
import os
from pathlib import Path
from urllib.parse import urlparse

import pymysql


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("salida", type=Path)
    args = parser.parse_args()
    url = os.getenv("MYSQL_PUBLIC_URL") or os.getenv("DATABASE_URL")
    if not url:
        raise SystemExit("No se encontró MYSQL_PUBLIC_URL ni DATABASE_URL.")
    parsed = urlparse(url)
    connection = pymysql.connect(
        host=parsed.hostname,
        port=parsed.port or 3306,
        user=parsed.username,
        password=parsed.password,
        database=parsed.path.lstrip("/"),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )
    args.salida.parent.mkdir(parents=True, exist_ok=True)
    with connection, args.salida.open("w", encoding="utf-8", newline="\n") as output:
        cursor = connection.cursor()
        output.write("SET NAMES utf8mb4;\nSET FOREIGN_KEY_CHECKS=0;\n\n")
        cursor.execute("SHOW FULL TABLES WHERE Table_type='BASE TABLE'")
        tables = [next(iter(row.values())) for row in cursor.fetchall()]
        for table in tables:
            cursor.execute(f"SHOW CREATE TABLE `{table}`")
            create = cursor.fetchone()["Create Table"]
            output.write(f"DROP TABLE IF EXISTS `{table}`;\n{create};\n\n")
            cursor.execute(f"SELECT * FROM `{table}`")
            rows = cursor.fetchall()
            for row in rows:
                columns = ",".join(f"`{column}`" for column in row)
                values = ",".join(connection.escape(value) for value in row.values())
                output.write(f"INSERT INTO `{table}` ({columns}) VALUES ({values});\n")
            if rows:
                output.write("\n")
        cursor.execute("SHOW FULL TABLES WHERE Table_type='VIEW'")
        views = [next(iter(row.values())) for row in cursor.fetchall()]
        for view in views:
            cursor.execute(f"SHOW CREATE VIEW `{view}`")
            create = cursor.fetchone()["Create View"]
            output.write(f"DROP VIEW IF EXISTS `{view}`;\n{create};\n\n")
        output.write("SET FOREIGN_KEY_CHECKS=1;\n")
    print(f"Respaldo creado: {args.salida}")


if __name__ == "__main__":
    main()
