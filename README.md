# Sistema de gestión acuícola Pacific Gold

Aplicación web para centralizar el seguimiento operativo de piscinas, personal,
actividades, alimento, alertas y reportes.

## Componentes

- **Backend:** Python y API HTTP.
- **Frontend:** HTML, CSS y JavaScript.
- **Base de datos:** MariaDB en desarrollo y MySQL 8 en producción.
- **Despliegue:** Railway.

## Estructura

```text
database/              Esquema, migraciones y herramientas de base de datos
docs/                  Documentación funcional, manuales y diagramas
public/                Interfaz web
  assets/css/          Estilos
  assets/images/       Recursos gráficos utilizados
  assets/js/           Lógica de las pantallas
tests/                 Pruebas automatizadas
tools/                 Utilidades de verificación y documentación
server.py              Servidor y API de la aplicación
```

## Ejecución local

1. Crear un archivo `.env` usando `.env.example` como referencia.
2. Instalar dependencias:

```powershell
python -m pip install -r requirements.txt
```

3. Iniciar el servidor:

```powershell
python server.py
```

4. Abrir `http://127.0.0.1:8000`.

## Base de datos

El esquema completo se encuentra en `database/schema/schema.sql`. Los cambios
para bases existentes están numerados dentro de `database/migrations/`.

Las credenciales, respaldos y archivos con información real no deben publicarse
en el repositorio.
