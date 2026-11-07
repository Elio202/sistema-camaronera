"""Permite registrar trabajos varios sin asociarlos a una piscina."""

import os

import pymysql


def main():
    connection = pymysql.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        database=os.getenv("DB_NAME", "pacific_gold"),
    )
    with connection:
        cursor = connection.cursor()
        cursor.execute(
            "ALTER TABLE actividades "
            "MODIFY COLUMN piscina_id INT UNSIGNED NULL"
        )
        cursor.execute(
            "SELECT IS_NULLABLE FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='actividades' "
            "AND COLUMN_NAME='piscina_id'"
        )
        nullable = cursor.fetchone()[0]
    if nullable != "YES":
        raise SystemExit("No se pudo habilitar piscina_id como opcional.")
    print("Actividades sin piscina habilitadas correctamente.")


if __name__ == "__main__":
    main()
