# ecommerce_api_reto_ia
Reto IA en ingeniería de Software UIS  

# E-commerce API

API REST para una tienda en línea, construida con **FastAPI**, **SQLAlchemy 2.0** y **MySQL**.
Incluye autenticación JWT, control de stock sin sobreventa, historial de pedidos con filtros
y paginación, y una suite de pruebas con cobertura mínima del 70 %.

## Contenido
1. [Características](#características)
2. [Arquitectura](#arquitectura)
3. [Estructura del proyecto](#estructura-del-proyecto)
4. [Requisitos](#requisitos)
5. [Instalación y configuración](#instalación-y-configuración)
6. [Cómo ejecutar la API](#cómo-ejecutar-la-api)
7. [Ejecución con Docker](#ejecución-con-docker)
8. [Documentación de la API](#documentación-de-la-api)
9. [Endpoints](#endpoints)
10. [Ejemplo de uso completo](#ejemplo-de-uso-completo)
11. [Pruebas](#pruebas)
12. [Decisiones de diseño y seguridad](#decisiones-de-diseño-y-seguridad)
13. [Limitaciones conocidas](#limitaciones-conocidas)
14. [Solución de problemas](#solución-de-problemas)

## Características
- Registro e inicio de sesión con **JWT** (contraseñas cifradas con bcrypt).
- Roles: usuario normal y administrador.
- Catálogo de productos con **paginación** (`limit` y `offset`).
- Creación de pedidos con **validación de stock**, bloqueo de filas y transacción atómica.
- Descuento porcentual configurable por variables de entorno.
- **Historial de pedidos** por usuario con nombres de producto, filtros por estado y fecha,
  y paginación.
- Limitación de tasa en login y registro, CORS configurable y errores de BD sin filtrar detalles.
- Documentación interactiva OpenAPI (Swagger UI y ReDoc).

## Arquitectura

La aplicación sigue una arquitectura en **capas**; cada capa solo depende de la inferior.

```
Cliente (Swagger, curl, frontend)
        │  HTTP / JSON
        ▼
┌──────────────────────────────────────────────┐
│ main.py: app, CORS, rate limit, manejo de    │
│          errores globales                    │
├──────────────────────────────────────────────┤
│ routers/      CAPA HTTP                      │
│  auth · users · products · orders            │
│  Reciben la petición, validan permisos,      │
│  traducen excepciones a códigos HTTP         │
├──────────────────────────────────────────────┤
│ services/     CAPA DE NEGOCIO                │
│  order_service · pricing                     │
│  Reglas: stock, descuento, historial         │
├──────────────────────────────────────────────┤
│ models.py     CAPA DE DATOS (SQLAlchemy ORM) │
│ database.py   Engine, sesión y pool          │
└──────────────────────────────────────────────┘
        │
        ▼
     MySQL (ecommerce_db)

Transversales: config.py (variables de entorno) · schemas.py (Pydantic)
               auth.py (JWT, hash, dependencias de seguridad)
```

### Responsabilidad de cada capa
| Capa | Responsabilidad | No debe |
|---|---|---|
| `routers/` | HTTP: parámetros, códigos de estado, permisos, `commit`/`rollback` | Contener reglas de negocio |
| `services/` | Reglas de negocio y consultas complejas; lanza excepciones propias | Conocer HTTP ni hacer `commit` |
| `models.py` | Tablas y relaciones | Contener lógica de negocio |
| `schemas.py` | Validar entrada y definir la forma de las respuestas | Acceder a la BD |

### Modelo de datos
```
users 1 ──── * orders 1 ──── * order_items * ──── 1 products
```
| Tabla | Campos principales |
|---|---|
| `users` | id, name, email (único), hashed_password, is_admin |
| `products` | id, name, price (Numeric), stock (≥ 0) |
| `orders` | id, user_id, total_price, status, created_at |
| `order_items` | id, order_id, product_id, quantity, unit_price (precio cobrado) |

### Flujo de `POST /orders/`
1. `get_current_user` valida el JWT y obtiene el usuario.
2. Pydantic valida el cuerpo: 1 a 50 líneas, sin duplicados, cantidades de 1 a 100.
3. El servicio consulta **todos** los productos en una sola consulta con
   `SELECT ... FOR UPDATE` (bloquea las filas y evita el problema N+1).
4. Por cada línea: verifica que exista, que haya stock, aplica el descuento y descuenta.
5. El router hace `commit`; ante cualquier error hace `rollback` y nada queda a medias.

## Estructura del proyecto
```
ecommerce_api/
├── .env.example          Plantilla de configuración
├── .gitignore
├── README.md
├── requirements.txt
├── requirements-dev.txt  Dependencias de pruebas
├── pytest.ini            Configuración de pytest y cobertura mínima
├── Dockerfile            Imagen de la API (slim, usuario no-root)
├── docker-compose.yml    Orquesta api + MySQL con volumen persistente
├── .dockerignore
├── app/
│   ├── main.py           Aplicación FastAPI y middleware
│   ├── config.py         Configuración desde variables de entorno
│   ├── database.py       Engine, sesión y Base
│   ├── limiter.py        Limitador de tasa (slowapi)
│   ├── auth.py           Hash, JWT y dependencias de seguridad
│   ├── models.py         Modelos SQLAlchemy
│   ├── schemas.py        Esquemas Pydantic
│   ├── responses.py      Respuestas de error para OpenAPI
│   ├── routers/          auth, users, products, orders
│   └── services/         order_service, pricing
└── tests/                Pruebas unitarias y de integración
```

## Requisitos
- Python 3.10 o superior
- MySQL 8 (o MariaDB compatible)
- `pip` y `venv`

## Instalación y configuración

### 1. Entorno virtual y dependencias
```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Base de datos
Ejecuta en MySQL como administrador:
```sql
CREATE DATABASE ecommerce_db CHARACTER SET utf8mb4;
CREATE USER 'ecommerce_app'@'localhost' IDENTIFIED BY 'UNA_CLAVE_FUERTE';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE ON ecommerce_db.* TO 'ecommerce_app'@'localhost';
```
La API usa un usuario dedicado, **nunca `root`**. El permiso `CREATE` es necesario porque
las tablas se crean automáticamente en el primer arranque.

### 3. Variables de entorno
```bash
cp .env.example .env
openssl rand -hex 32        # copia el resultado en SECRET_KEY
```
| Variable | Obligatoria | Descripción | Ejemplo |
|---|:---:|---|---|
| `DATABASE_URL` | Sí | Cadena de conexión | `mysql+pymysql://ecommerce_app:CLAVE@localhost:3306/ecommerce_db` |
| `SECRET_KEY` | Sí | Clave de firma JWT (mínimo 32 caracteres) | salida de `openssl rand -hex 32` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | Duración del token (por defecto 30) | `30` |
| `CORS_ORIGINS` | No | Orígenes permitidos, lista JSON | `["http://localhost:3000"]` |
| `DISCOUNT_THRESHOLD` | No | Precio sobre el cual aplica descuento (100) | `100` |
| `DISCOUNT_PERCENT` | No | Porcentaje de descuento (10) | `10` |

> El archivo `.env` contiene secretos: **no lo subas al repositorio** (ya está en `.gitignore`).

## Cómo ejecutar la API
```bash
uvicorn app.main:app --reload
```
Disponible en `http://localhost:8000`. En producción, quita `--reload` y usa
`--host 0.0.0.0 --workers 4`.

### Crear un administrador
Los usuarios se registran como usuarios normales. Para volver administrador a uno:
```sql
UPDATE users SET is_admin = 1 WHERE email = 'admin@correo.com';
```

## Ejecución con Docker

Levanta la API y MySQL 8 en contenedores, con los datos de la base de datos en un
volumen persistente.

### Requisitos
- Docker Desktop (Windows/macOS) o Docker Engine con el plugin `docker compose`

### Pasos
1. En `.env` define, además de `SECRET_KEY`, dos claves para MySQL:
   ```bash
   MYSQL_ROOT_PASSWORD=<clave-root-larga>
   MYSQL_PASSWORD=<clave-app-larga>
   ```
   Genera claves con `openssl rand -hex 16`.
2. Construye e inicia:
   ```bash
   docker compose up -d --build
   ```
3. Verifica:
   ```bash
   curl http://localhost:8000/products/
   docker compose logs -f api
   ```
   La API queda en `http://localhost:8000` (docs en `/docs`). Las tablas se crean
   solas en el primer arranque.

### Persistencia
- MySQL guarda sus datos en el volumen nombrado `ecommerce_mysql_data` (montado en
  `/var/lib/mysql`): sobrevive a `docker compose down` y a reinicios.
- `docker compose down` detiene todo **conservando** los datos.
- `docker compose down -v` borra también el volumen: **pierdes la base de datos**.

### Qué hace cada pieza
| Pieza | Detalle |
|---|---|
| `Dockerfile` | Python 3.12 slim, dependencias en capa cacheada, usuario no-root (`appuser`), `HEALTHCHECK` sobre `/health` |
| Servicio `mysql` | Imagen `mysql:8.0`; crea la BD `ecommerce_db` y el usuario `ecommerce_app` (mínimo privilegio, sin root); `healthcheck` con `mysqladmin ping`; publica 3306 solo en `127.0.0.1` |
| Servicio `api` | Construye la imagen local; espera a que MySQL esté sano (`depends_on: service_healthy`); se conecta por la red interna de Compose (`mysql:3306`); publica `8000:8000` |

### Notas
- El `DATABASE_URL` del `.env` local (por ejemplo SQLite) **no afecta** a los
  contenedores: la API en Docker construye su propia `DATABASE_URL` desde
  `MYSQL_PASSWORD` apuntando a `mysql:3306`.
- `.env` está en `.gitignore`: no subas las claves al repositorio.
- Para producción real: pon HTTPS delante (proxy reverso), no publiques 3306,
  usa secretos del orquestador y considera Alembic para migraciones.

## Documentación de la API
| URL | Descripción |
|---|---|
| `http://localhost:8000/docs` | Swagger UI interactivo (permite probar con **Authorize**) |
| `http://localhost:8000/redoc` | ReDoc, vista de lectura |
| `http://localhost:8000/openapi.json` | Especificación OpenAPI 3 |

## Endpoints
| Método | Ruta | Acceso | Descripción |
|---|---|---|---|
| GET | `/health` | Público | Health check para probes/monitores |
| POST | `/auth/login` | Público (5/min) | Devuelve un token JWT |
| POST | `/users/` | Público (10/min) | Registra un usuario |
| GET | `/users/me` | Autenticado | Perfil del usuario actual |
| GET | `/users/{user_id}/orders` | Dueño o admin | Historial con nombres de producto |
| GET | `/products/` | Público | Lista productos (`limit`, `offset`) |
| POST | `/products/` | Admin | Crea un producto |
| POST | `/orders/` | Autenticado | Crea un pedido |

### Parámetros de `GET /users/{user_id}/orders`
| Parámetro | Tipo | Descripción |
|---|---|---|
| `status` | `pending` \| `paid` \| `cancelled` | Filtra por estado |
| `date_from` | fecha ISO 8601 | Pedidos desde esa fecha |
| `date_to` | fecha ISO 8601 | Pedidos hasta esa fecha |
| `limit` | 1 a 100 (20) | Tamaño de página |
| `offset` | ≥ 0 (0) | Registros a saltar |

### Códigos de respuesta
| Código | Significado |
|---|---|
| 200 / 201 | Operación correcta / recurso creado |
| 400 | Producto inexistente en el pedido |
| 401 | Token ausente, inválido o expirado; credenciales incorrectas |
| 403 | Sin permisos (otro usuario o no es admin) |
| 404 | Usuario no encontrado |
| 409 | Email duplicado o stock insuficiente |
| 422 | Datos inválidos |
| 429 | Límite de solicitudes superado |
| 500 | Error interno (sin detalles internos) |

## Ejemplo de uso completo
```bash
# 1. Registrar usuario
curl -X POST http://localhost:8000/users/ -H "Content-Type: application/json" \
  -d '{"name":"Ana Pérez","email":"ana@correo.com","password":"Clave12345"}'

# 2. Iniciar sesión (formulario, no JSON)
curl -X POST http://localhost:8000/auth/login \
  -d "username=ana@correo.com&password=Clave12345"
# → {"access_token":"eyJ...","token_type":"bearer"}

TOKEN="eyJ..."

# 3. Ver productos (página 2 de 10 en 10)
curl "http://localhost:8000/products/?limit=10&offset=10"

# 4. Crear un pedido
curl -X POST http://localhost:8000/orders/ \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"items":[{"product_id":1,"quantity":2}]}'

# 5. Historial con filtros
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/users/1/orders?status=pending&limit=5&offset=0"
```

Respuesta del historial:
```json
[
  {
    "id": 7,
    "total_price": "360.00",
    "status": "pending",
    "created_at": "2026-11-02T15:30:00Z",
    "items": [
      {"product_id": 3, "product_name": "Teclado mecánico", "quantity": 2, "unit_price": "180.00"}
    ]
  }
]
```

## Pruebas

### Pasos
```bash
# 1. Instalar dependencias de prueba
pip install -r requirements-dev.txt

# 2. Ejecutar toda la suite (valida cobertura mínima de 70 %)
pytest

# Otras opciones
pytest -v                      # detalle por prueba
pytest tests/test_orders.py    # un archivo
pytest -k "history"            # por nombre
```
Las pruebas usan **SQLite en memoria**: no necesitan MySQL ni tocan tu base de datos real,
sin importar el contenido de tu `.env`.

### Qué se prueba
| Archivo | Tipo | Cubre |
|---|---|---|
| `test_pricing.py` | Unitaria | Descuento, umbral, redondeo |
| `test_schemas.py` | Unitaria | Validaciones de entrada |
| `test_models.py` | Unitaria | Restricciones y valores por defecto |
| `test_auth.py` | Unit. + integración | Hash, JWT válido/expirado/manipulado, roles |
| `test_users.py` | Integración | Registro, login, perfil, rate limit |
| `test_products.py` | Integración | Paginación y creación por admin |
| `test_orders.py` | Integración | Stock, descuento, atomicidad, rollback |
| `test_order_history.py` | Integración | Historial, autorización, filtros, paginación |
| `test_app.py` | Integración | Errores de BD, CORS |
| `test_docs.py` | Integración | Todos los endpoints documentados |

### Cobertura
`pytest` imprime la tabla de cobertura y falla si es menor a 70 %.
El reporte HTML queda en `htmlcov/index.html`.

### Prueba manual en Swagger
1. Abre `http://localhost:8000/docs`.
2. `POST /users/` → registra un usuario.
3. `POST /auth/login` → copia el `access_token`.
4. Pulsa **Authorize**, pega el token y confirma.
5. Como admin, crea productos con `POST /products/`.
6. `POST /orders/` → crea un pedido y verifica que el stock baje en `GET /products/`.
7. `GET /users/{id}/orders` → revisa el historial.

## Decisiones de diseño y seguridad
- **Sin credenciales en el código:** todo sale de variables de entorno; hay un usuario MySQL
  de mínimo privilegio.
- **Autorización:** el pedido toma el usuario del token (no del cuerpo) y el historial solo lo
  ve el dueño o un admin, para evitar accesos a datos ajenos (IDOR).
- **Dinero con `Decimal`/`Numeric`**, no `float`, para evitar errores de redondeo.
- **Sin sobreventa:** `SELECT ... FOR UPDATE` con orden fijo por id (evita deadlocks) y
  restricción `CHECK (stock >= 0)` como segunda defensa.
- **Sin N+1:** productos con `IN (...)` y historial con `selectinload`.
- **Precio histórico:** `order_items.unit_price` guarda lo que se cobró, aunque el precio
  del producto cambie después.
- **Errores genéricos:** los fallos de BD devuelven 500 sin detalles internos.

## Limitaciones conocidas
- **Bloqueo de filas solo en MySQL:** las pruebas usan SQLite, que ignora `FOR UPDATE`; la
  protección contra pedidos concurrentes solo se verifica en MySQL real.
- **Tablas con `create_all`:** se crean al arrancar, pero no se migran cambios de esquema.
  Para producción se recomienda Alembic.
- **Conexión MySQL sin SSL** y **dependencias en versiones fijas originales**: pendientes de
  revisar antes de un despliegue real.
- **Sin endpoints** para actualizar o cancelar pedidos, ni para editar o borrar productos.
- **Rate limit en memoria:** con varios workers cada proceso cuenta por separado.

## Solución de problemas
| Síntoma | Causa probable | Solución |
|---|---|---|
| `ValidationError` al iniciar | Falta `DATABASE_URL` o `SECRET_KEY` | Crea el `.env` desde `.env.example` |
| `secret_key` demasiado corta | Menos de 32 caracteres | `openssl rand -hex 32` |
| `Access denied` o `CREATE command denied` | Permisos del usuario MySQL | Revisa los `GRANT` |
| `Can't connect to MySQL server` | MySQL apagado o URL incorrecta | Verifica servicio, host y puerto |
| 401 en un endpoint protegido | Token expirado | Vuelve a iniciar sesión |
| Errores del `TestClient` al probar | `httpx` incompatible | `pip install httpx==0.27.2` |