# Entrega final — Sistema Pacific Gold

**Estudiante:** Elio Danilo Marroquin Alvarez  
**Fecha:** 7 de noviembre de 2026  
**Aplicación:** https://web-production-5dd5b.up.railway.app

## Contenido

- `01_Documentacion`: documento del proyecto, manual de usuario, manual técnico y guía de presentación.
- `02_Codigo_Fuente`: código de la aplicación sin claves, respaldos ni datos locales.
- `03_Base_Datos`: esquema completo y migraciones incrementales.
- `04_Pruebas`: pruebas automatizadas y manual de pruebas.
- `05_Despliegue`: archivos y guía necesarios para instalar o desplegar.

## Ejecución local

1. Copiar `.env.example` como `.env` y configurar MariaDB.
2. Instalar dependencias con `python -m pip install -r requirements.txt`.
3. Preparar la base mediante `database/schema/schema.sql` y las migraciones necesarias.
4. Ejecutar `python server.py`.
5. Abrir `http://127.0.0.1:8000/login.html`.

## Seguridad

El ZIP no contiene `.env`, contraseñas, tokens, claves del sensor, respaldos productivos ni sesiones. Los datos reales permanecen en las bases autorizadas.
