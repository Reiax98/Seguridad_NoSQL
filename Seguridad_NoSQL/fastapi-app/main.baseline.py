from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel, Field
from pymongo import MongoClient
from bson import ObjectId
from bson.errors import InvalidId
import os
import requests

app = FastAPI(title="API NoSQL vulnerable")

# Conexion a MongoDB sin autenticacion
mongo = MongoClient(
    os.getenv("MONGO_URI", "mongodb://mongo:27017"),
    serverSelectionTimeoutMS=5000
)

db = mongo[os.getenv("MONGO_DATABASE", "tienda")]

ELASTIC_URL = os.getenv(
    "ELASTIC_URL",
    "http://elasticsearch:9200"
)


class Pedido(BaseModel):
    producto: str = Field(min_length=1, max_length=100)
    cantidad: int = Field(gt=0, le=1000)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/pedidos")
def crear_pedido(pedido: Pedido):
    resultado = db.pedidos.insert_one(
        pedido.model_dump()
    )
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


# LOGIN VULNERABLE A NOSQL INJECTION
@app.post("/login_mongo")
async def login(req: Request):
    data = await req.json()

    user = db.usuarios.find_one({
        "username": data.get("username"),
        "password": data.get("password")
    })

    if user:
        return {"msg": "ok"}

    raise HTTPException(status_code=401, detail="Bad creds")


# BUSQUEDA VULNERABLE EN ELASTICSEARCH
@app.get("/articulos")
def buscar_articulos(q: str = "*"):
    respuesta = requests.get(
        f"{ELASTIC_URL}/articulos/_search",
        params={"q": q},
        timeout=5
    )

    respuesta.raise_for_status()

    return respuesta.json()
