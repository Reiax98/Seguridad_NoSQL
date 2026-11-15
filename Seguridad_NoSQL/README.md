# Laboratorio de Seguridad NoSQL

Laboratorio local para analizar la seguridad de **MongoDB** y **Elasticsearch** integrados en una API **FastAPI**. El proyecto permite comparar una configuración vulnerable con otra que incorpora controles de seguridad.

> [!WARNING]
> El escenario vulnerable es intencionadamente inseguro. Ejecútalo solo en tu equipo, con datos ficticios y sin exponer sus puertos a Internet ni a redes compartidas.

## Contenido

- [Requisitos](#requisitos)
- [Preparación](#preparación)
- [Arranque de Docker](#arranque-de-docker)
- [Escenario vulnerable](#escenario-vulnerable)
- [Escenario protegido](#escenario-protegido)
- [Copias de seguridad](#copias-de-seguridad)
- [Detener o reiniciar el laboratorio](#detener-o-reiniciar-el-laboratorio)
- [Archivos que no se deben subir](#archivos-que-no-se-deben-subir-a-github)

## Requisitos

- Linux.
- Docker Engine y Docker Compose (`docker compose`).
- `curl` y Python 3.
- `mongosh` y `nmap` para algunas comprobaciones opcionales.

Comprueba la instalación:

```bash
docker --version
docker compose version
python3 --version
```

## Preparación

Clona el repositorio y accede al directorio:

```bash
git clone https://github.com/Reiax98/Seguridad_NoSQL.git
cd Seguridad_NoSQL
```

Crea el archivo `.env` a partir de la plantilla, si está incluida:

```bash
cp .env.example .env
```

Edita `.env` y configura las variables que utilice `docker-compose.yml`. En el escenario protegido se utilizan credenciales para los usuarios de MongoDB y Elasticsearch. Por ejemplo:

```dotenv
MONGO_ROOT_USER=admin_local
MONGO_ROOT_PASSWORD=CAMBIAR_POR_UNA_CLAVE_LOCAL
MONGO_APP_USER=app_local
MONGO_APP_PASSWORD=CAMBIAR_POR_UNA_CLAVE_LOCAL
ELASTIC_USER=elastic_local
ELASTIC_PASSWORD=CAMBIAR_POR_UNA_CLAVE_LOCAL
ELASTIC_APP_USER=app_elastic_local
ELASTIC_APP_PASSWORD=CAMBIAR_POR_UNA_CLAVE_LOCAL
```

Sustituye los valores de ejemplo por credenciales propias y comprueba que los nombres coinciden con los definidos en los archivos de configuración. No subas el `.env` a GitHub.

Comprueba también que existen los certificados requeridos por el escenario protegido en el directorio `certs/`. No incluyas claves privadas en el repositorio.

## Arranque de Docker

Desde la raíz del proyecto, construye e inicia los servicios:

```bash
docker compose -p nosql-baseline up -d --build
```

Comprueba el estado de los contenedores:

```bash
docker compose -p nosql-baseline ps
```

Consulta los registros:

```bash
docker compose -p nosql-baseline logs --tail=100
```

El laboratorio utiliza estos puertos del equipo anfitrión, siempre que estén publicados en `docker-compose.yml`:

| Servicio | Puerto | Uso |
|---|---:|---|
| MongoDB | `27017` | Usuarios y pedidos |
| Elasticsearch | `9200` | Índice y búsqueda de artículos |
| FastAPI vulnerable | `8000` | API mediante HTTP |
| FastAPI protegida | `8443` | API mediante HTTPS |

### Inicializar los datos

El script `init_mongo.js` carga los datos iniciales de MongoDB cuando se crea por primera vez el volumen, siempre que esté montado en el directorio de inicialización del contenedor. Si el volumen ya existía, el script no se ejecutará de nuevo automáticamente.

Para inicializar Elasticsearch en el escenario vulnerable:

```bash
chmod +x scripts/init_elastic.sh
./scripts/init_elastic.sh
```

Este script recrea el índice `articulos` y carga documentos de prueba. No lo ejecutes si necesitas conservar los documentos actuales.

Comprueba los datos de MongoDB:

```bash
docker compose -p nosql-baseline exec mongo mongosh tienda --quiet --eval 'db.usuarios.find({}, {_id:0}).toArray()'
docker compose -p nosql-baseline exec mongo mongosh tienda --quiet --eval 'db.pedidos.find().toArray()'
```

Comprueba el índice y los documentos de Elasticsearch en el escenario vulnerable:

```bash
curl -i 'http://127.0.0.1:9200/_cat/indices?v'
curl -s 'http://127.0.0.1:9200/articulos/_search?q=*' | python3 -m json.tool
```

## Escenario vulnerable

Antes de ejecutar estas pruebas, comprueba que FastAPI está utilizando `main.baseline.py` y que los servicios están desplegados con la configuración vulnerable. El proyecto contiene también `main.py`, correspondiente al escenario protegido. Verifica en la configuración de Docker qué versión de la aplicación se está copiando o montando antes de reconstruir el contenedor.

### Comprobar la API

```bash
curl -i http://127.0.0.1:8000/health
curl -i http://127.0.0.1:8000/pedidos
curl -i -X POST http://127.0.0.1:8000/login_mongo \
  -H 'Content-Type: application/json' \
  -d '{"username":"alice","password":"secreto123"}'
curl -i 'http://127.0.0.1:8000/articulos?q=teclado'
```

### Probar las operaciones CRUD

Este bloque crea un pedido temporal, lo consulta, lo actualiza y finalmente lo elimina:

```bash
RESPUESTA=$(curl -sS -X POST http://127.0.0.1:8000/pedidos \
  -H 'Content-Type: application/json' \
  -d '{"producto":"Libreta","cantidad":2}')

echo "$RESPUESTA"
ID=$(echo "$RESPUESTA" | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')

curl -sS http://127.0.0.1:8000/pedidos
curl -i -X PUT "http://127.0.0.1:8000/pedidos/$ID" \
  -H 'Content-Type: application/json' \
  -d '{"producto":"Libreta actualizada","cantidad":5}'
curl -i -X DELETE "http://127.0.0.1:8000/pedidos/$ID"
curl -sS http://127.0.0.1:8000/pedidos
```

### Comprobar las vulnerabilidades

**Inyección NoSQL en el login:**

```bash
curl -i -X POST http://127.0.0.1:8000/login_mongo \
  -H 'Content-Type: application/json' \
  -d '{"username":"alice","password":{"$ne":null}}'
```

**Acceso anónimo a MongoDB:**

```bash
docker compose -p nosql-baseline exec mongo mongosh tienda
```

Una vez dentro de `mongosh`:

```javascript
db.usuarios.find().pretty()
db.pedidos.find().pretty()
```

**Acceso abierto a Elasticsearch:**

```bash
curl -i 'http://127.0.0.1:9200/_cat/indices?v'
curl -s 'http://127.0.0.1:9200/articulos/_search?q=*' | python3 -m json.tool
```

También se puede crear, insertar un documento y eliminar un índice temporal:

```bash
curl -i -X PUT 'http://127.0.0.1:9200/indice_prueba'
curl -i -X POST 'http://127.0.0.1:9200/indice_prueba/_doc' \
  -H 'Content-Type: application/json' \
  -d '{"title":"Documento de prueba"}'
curl -i -X DELETE 'http://127.0.0.1:9200/indice_prueba'
```

**Reconocimiento de puertos (opcional):**

```bash
nmap -sV -p 27017,9200,8000 127.0.0.1
```

## Escenario protegido

Cambia la configuración para que Docker ejecute `main.py` y utilice la configuración protegida de MongoDB, Elasticsearch y FastAPI. Asegúrate de que `.env` y los certificados locales están preparados. Después, reconstruye los servicios:

```bash
docker compose -p nosql-baseline up -d --build
```

### Comprobar HTTPS y la validación de entradas

Comprueba FastAPI mediante HTTPS y la CA del laboratorio:

```bash
curl --cacert certs/ca.crt -i https://127.0.0.1:8443/health
```

Repite la prueba de inyección. La API protegida debe rechazar el objeto JSON como tipo de contraseña no válido (HTTP `422`):

```bash
curl --cacert certs/ca.crt -i -X POST https://127.0.0.1:8443/login_mongo \
  -H 'Content-Type: application/json' \
  -d '{"username":"alice","password":{"$ne":null}}'
```

### Comprobar autenticación y permisos de Elasticsearch

Una petición sin credenciales debe ser rechazada:

```bash
curl --cacert certs/ca.crt -i \
  'https://127.0.0.1:9200/articulos/_search'
```

Para probar la búsqueda desde FastAPI con paginación:

```bash
curl --cacert certs/ca.crt -i \
  'https://127.0.0.1:8443/articulos?q=teclado&page=1&size=1'
```

Carga las variables del archivo `.env` en la terminal para probar directamente el usuario de aplicación de Elasticsearch:

```bash
set -a
source .env
set +a
```

Consulta el índice con el usuario limitado:

```bash
curl --cacert certs/ca.crt -u "$ELASTIC_APP_USER:$ELASTIC_APP_PASSWORD" \
  'https://127.0.0.1:9200/articulos/_search?pretty'
```

La siguiente operación intenta crear un índice. El usuario de aplicación no debe tener permisos para realizarla (normalmente HTTP `403`):

```bash
curl --cacert certs/ca.crt -u "$ELASTIC_APP_USER:$ELASTIC_APP_PASSWORD" \
  -i -X PUT 'https://127.0.0.1:9200/indice_verificacion'
```

### Comprobar el límite de peticiones y los registros

El login tiene un límite de cinco peticiones por minuto. La sexta petición dentro del mismo minuto debe recibir HTTP `429`:

```bash
for i in {1..6}; do
  curl --cacert certs/ca.crt -sS -o /dev/null -w '%{http_code}\n' \
    -X POST https://127.0.0.1:8443/login_mongo \
    -H 'Content-Type: application/json' \
    -d '{"username":"alice","password":"incorrecta"}'
done
```

Consulta los registros de los contenedores:

```bash
docker compose -p nosql-baseline logs --tail=200
```

## Copias de seguridad

Estas operaciones son opcionales. Requieren que las credenciales, los certificados y el repositorio de snapshots estén configurados previamente.

### Snapshot de Elasticsearch

Carga las variables del archivo `.env` si todavía no lo has hecho:

```bash
set -a
source .env
set +a
SNAPSHOT="snapshot-$(date +%Y%m%d-%H%M%S)"
```

Crea y consulta un snapshot del índice `articulos`:

```bash
curl --cacert certs/ca.crt -u "$ELASTIC_USER:$ELASTIC_PASSWORD" \
  -X PUT "https://127.0.0.1:9200/_snapshot/lab_repo/${SNAPSHOT}?wait_for_completion=true" \
  -H 'Content-Type: application/json' \
  -d '{"indices":"articulos","include_global_state":false}'

curl --cacert certs/ca.crt -u "$ELASTIC_USER:$ELASTIC_PASSWORD" \
  'https://127.0.0.1:9200/_snapshot/lab_repo/_all?pretty'
```

### Backup de MongoDB

La versión de MongoDB Database Tools utilizada en el laboratorio admite las opciones `--ssl` y `--sslCAFile` para la conexión TLS. El siguiente comando crea un archivo comprimido en `backups/`:

```bash
mkdir -p backups

docker compose -p nosql-baseline exec -T mongo sh -lc \
  'mongodump --host 127.0.0.1 --port 27017 \
    --username "$MONGO_ROOT_USER" --password "$MONGO_ROOT_PASSWORD" \
    --authenticationDatabase admin --db tienda \
    --ssl --sslCAFile /etc/mongo/tls/ca.crt \
    --archive --gzip' \
  > "backups/tienda-$(date +%Y%m%d-%H%M%S).archive.gz"
```

## Detener o reiniciar el laboratorio

Detener los contenedores sin borrar los datos:

```bash
docker compose -p nosql-baseline down
```

Volver a iniciar los servicios:

```bash
docker compose -p nosql-baseline up -d --build
```

Para borrar también los volúmenes y reiniciar los datos desde cero:

```bash
docker compose -p nosql-baseline down -v
```

> **Atención:** `down -v` elimina los volúmenes de Docker y los datos guardados en MongoDB y Elasticsearch.

## Archivos que no se deben subir a GitHub

No incluyas en el repositorio:

- `.env` ni archivos con contraseñas reales.
- Claves privadas de certificados (`.key`, `.pem` privados, `.p12`, `.pfx`).
- Copias de seguridad, archivos BSON, archives ni snapshots.
- Directorios de datos o volúmenes de Docker.

Sí puedes subir el código, `docker-compose.yml`, scripts, `init_mongo.js`, este README y un `.env.example` con valores ficticios. Revisa siempre los archivos antes de hacer el commit.
