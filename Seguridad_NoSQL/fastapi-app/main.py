from fastapi import FastAPI, Request, HTTPException, Query
from pydantic import BaseModel, Field, StrictStr
from pymongo import MongoClient
from bson import ObjectId
from bson.errors import InvalidId

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from collections import defaultdict, deque
import hashlib
import hmac
import logging
import os
import time
import requests


# Dodne se guarará el registro de actividad
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s"
)

logger = logging.getLogger("security")


# Limitación de peticiones
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri="memory://"
)

app = FastAPI(title="API NoSQL protegida")

app.state.limiter = limiter
app.add_exception_handler(
    RateLimitExceeded,
    _rate_limit_exceeded_handler
)


# Conexión protegida con MongoDB
mongo = MongoClient(
    host=os.environ["MONGO_HOST"],
    port=int(os.getenv("MONGO_PORT", "27017")),
    username=os.environ["MONGO_USER"],
    password=os.environ["MONGO_PASSWORD"],
    authSource=os.environ["MONGO_AUTH_SOURCE"],
    tls=True,
    tlsCAFile=os.environ["MONGO_CA"],
    serverSelectionTimeoutMS=5000
)
db = mongo[os.getenv("MONGO_DATABASE", "tienda")]


# Conexión protegida con Elasticsearch
ELASTIC_URL = os.environ["ELASTIC_URL"]
ELASTIC_USER = os.environ["ELASTIC_USER"]
ELASTIC_PASSWORD = os.environ["ELASTIC_PASSWORD"]
ELASTIC_CA = os.environ["ELASTIC_CA"]


# Seguimiento de eventos por IP
eventos = defaultdict(deque)


def registrar_evento(tipo, request, umbral):
    ip = get_remote_address(request) or "desconocida"
    clave = (tipo, ip)
    ahora = time.monotonic()

    cola = eventos[clave]

    while cola and ahora - cola[0] > 60:
        cola.popleft()

    cola.append(ahora)

    if len(cola) == umbral:
        logger.warning(
            "SECURITY_ALERT evento=%s ip=%s cantidad=%s periodo=60s",
            tipo,
            ip,
            len(cola)
        )


def verificar_password(password, usuario):
    try:
        salt = bytes.fromhex(usuario["password_salt"])
        iteraciones = int(usuario["password_iterations"])

        calculada = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            iteraciones
        ).hex()

        return hmac.compare_digest(
            calculada,
            usuario["password_hash"]
        )
    except (KeyError, ValueError, TypeError):
        return False


# Modelos
class Pedido(BaseModel):
    producto: str = Field(min_length=1, max_length=100)
    cantidad: int = Field(gt=0, le=1000)


class LoginRequest(BaseModel):
    username: StrictStr
    password: StrictStr


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/pedidos")
def crear_pedido(pedido: Pedido):
    resultado = db.pedidos.insert_one(pedido.model_dump())
    return {"id": str(resultado.inserted_id)}


@app.get("/pedidos")
def consultar_pedidos():
    pedidos = list(db.pedidos.find())

    for pedido in pedidos:
        pedido["_id"] = str(pedido["_id"])

    return pedidos


@app.put("/pedidos/{pedido_id}")
def actualizar_pedido(pedido_id: str, pedido: Pedido):
    try:
        oid = ObjectId(pedido_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="ID no valido")

    resultado = db.pedidos.update_one(
        {"_id": oid},
        {"$set": pedido.model_dump()}
    )

    if resultado.matched_count == 0:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")

    return {"msg": "Pedido actualizado"}


@app.delete("/pedidos/{pedido_id}")
def eliminar_pedido(pedido_id: str):
    try:
        oid = ObjectId(pedido_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="ID no valido")

    resultado = db.pedidos.delete_one({"_id": oid})

    if resultado.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")

    return {"msg": "Pedido eliminado"}


# Login protegido contra NoSQL injection
@app.post("/login_mongo")
@limiter.limit("5/minute")
def login(data: LoginRequest, request: Request):
    usuario = db.usuarios.find_one({
        "username": data.username
    })

    if usuario and verificar_password(data.password, usuario):
        return {"msg": "ok"}

    ip = get_remote_address(request) or "desconocida"

    logger.warning(
        "LOGIN_FAILED ip=%s username=%s",
        ip,
        data.username
    )

    registrar_evento("login_fallido", request, 5)

    raise HTTPException(
        status_code=401,
        detail="Credenciales incorrectas"
    )


@app.get("/articulos")
@limiter.limit("30/minute")
def buscar_articulos(
    request: Request,
    q: str = Query(min_length=1, max_length=100),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=50)
):
    registrar_evento("pico_busquedas", request, 20)

    if not q.strip():
        raise HTTPException(status_code=422, detail="Consulta vacia")

    consulta = {
        "from": (page - 1) * size,
        "size": size,
        "query": {
            "match": {
                "title": {
                    "query": q.strip(),
                    "operator": "and"
                }
            }
        }
    }

    try:
        respuesta = requests.post(
            f"{ELASTIC_URL}/articulos/_search",
            json=consulta,
            auth=(ELASTIC_USER, ELASTIC_PASSWORD),
            verify=ELASTIC_CA,
            timeout=5
        )

        respuesta.raise_for_status()
        return respuesta.json()

    except requests.RequestException:
        logger.exception("Error en la consulta a Elasticsearch")
        raise HTTPException(
            status_code=502,
            detail="Error consultando Elasticsearch"
        )
