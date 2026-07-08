# TraceReq

Plataforma web para la gestión de requerimientos de software: requerimientos funcionales (RF) y no funcionales (RNF), casos de uso, trazabilidad entre requerimientos y cobertura, con un dashboard de métricas.

## Características

- **Proyectos**: agrupan requerimientos y casos de uso.
- **Requerimientos funcionales y no funcionales**: identificador autogenerado (`RF-001`, `RF-002`, `RNF-001`, ...), prioridad, estado, categoría (para RNF), historial de cambios y comentarios.
- **Casos de uso**: identificador autogenerado (`CU-001`, `CU-002`, ...), vinculados a requerimientos funcionales.
- **Trazabilidad**: relaciones entre requerimientos (`depende de`, `refina`, `contradice`), matriz de cobertura requerimiento × caso de uso y grafo interactivo de dependencias.
- **Dashboard**: métricas generales, cobertura de requerimientos, gráficas de distribución por estado/prioridad/tipo.
- **Exportación**: descarga de los datos de un proyecto en CSV o JSON.
- Todas las fechas se registran en hora de Perú (UTC-5).

## Requisitos previos

- Python 3.9 o superior
- Un servidor MySQL en ejecución (local o remoto)

## Instalación

1. Clonar el repositorio y entrar a la carpeta del proyecto:

   ```bash
   git clone <url-del-repositorio>
   cd tracereq-desde-cero
   ```

2. Crear y activar un entorno virtual:

   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # Linux / macOS
   source venv/bin/activate
   ```

3. Instalar las dependencias:

   ```bash
   pip install -r requirements.txt
   ```

4. Crear la base de datos en MySQL (el nombre debe coincidir con `DB_NAME` del paso siguiente):

   ```sql
   CREATE DATABASE tracereq;
   ```

5. Copiar el archivo de variables de entorno de ejemplo y completarlo con tus datos:

   ```bash
   cp .env.example .env
   ```

   | Variable | Descripción | Valor por defecto |
   |---|---|---|
   | `SECRET_KEY` | Clave secreta de Flask | `cambia-esta-clave` |
   | `DB_USER` | Usuario de MySQL | `root` |
   | `DB_PASSWORD` | Contraseña de MySQL | *(vacío)* |
   | `DB_HOST` | Host de MySQL | `localhost` |
   | `DB_PORT` | Puerto de MySQL | `3306` |
   | `DB_NAME` | Nombre de la base de datos | `tracereq` |

6. Ejecutar la aplicación (crea las tablas automáticamente si no existen):

   ```bash
   python run.py
   ```

7. Abrir el navegador en [http://localhost:5000](http://localhost:5000).

## Uso

1. **Crear un proyecto** desde la sección *Proyectos*: este agrupará todos los requerimientos y casos de uso relacionados.
2. **Agregar requerimientos** desde *Requerimientos → Nuevo*: selecciona el proyecto y el tipo (funcional o no funcional); el identificador (`RF-XXX` / `RNF-XXX`) se asigna automáticamente y se muestra en el formulario antes de guardar.
3. **Agregar casos de uso** desde *Casos de Uso → Nuevo*: se generan como `CU-XXX` y pueden asociarse a uno o más requerimientos funcionales del proyecto.
4. **Definir trazabilidad** entre requerimientos (dependencia, refinamiento o contradicción) desde *Trazabilidad*, donde también se puede consultar la matriz de cobertura y el grafo interactivo de dependencias.
5. **Revisar el dashboard** para ver métricas generales, cobertura de requerimientos y distribución por estado/prioridad/tipo.
6. **Exportar** los datos de un proyecto en CSV o JSON desde la vista del proyecto.

## Estructura del proyecto

```
app/
  models.py            Modelos SQLAlchemy (Proyecto, Requerimiento, CasoUso, Trazabilidad, ...)
  utils.py             Utilidades comunes (hora de Peru, generación de identificadores)
  routes/              Blueprints de Flask (dashboard, proyectos, requerimientos, casos_uso, trazabilidad, exportar)
  templates/           Vistas Jinja2
  static/              CSS y JS
config.py              Configuración de la app y construcción de la URI de base de datos
run.py                 Punto de entrada de la aplicación
requirements.txt       Dependencias de Python
```
