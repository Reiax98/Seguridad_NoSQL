import os
import hashlib
import secrets

from pymongo import MongoClient


ITERACIONES = 600000

client = MongoClient(os.environ["MONGO_URI"])
db = client[os.getenv("MONGO_DATABASE", "tienda")]

usuarios = db.usuarios

migrados = 0

for usuario in usuarios.find({"password": {"$type": "string"}}):

    salt = secrets.token_bytes(16)

    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        usuario["password"].encode("utf-8"),
        salt,
        ITERACIONES
    ).hex()

    usuarios.update_one(
        {"_id": usuario["_id"]},
        {
            "$set": {
                "password_salt": salt.hex(),
                "password_hash": password_hash,
                "password_iterations": ITERACIONES
            },
            "$unset": {
                "password": ""
            }
        }
    )

    migrados += 1

print(f"Usuarios migrados correctamente: {migrados}")

client.close()
