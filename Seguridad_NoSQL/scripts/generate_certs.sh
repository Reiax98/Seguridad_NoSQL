#!/bin/bash
set -e

mkdir -p certs
cd certs

# Crear autoridad certificadora
openssl req -x509 -newkey rsa:4096 -sha256 -days 365 \
  -nodes -keyout ca.key \
  -out ca.crt \
  -subj "/CN=NoSQL-Lab-CA"

crear_certificado() {
    nombre="$1"
    san="$2"

    openssl req -new -newkey rsa:2048 -nodes \
      -keyout "${nombre}.key" \
      -out "${nombre}.csr" \
      -subj "/CN=${nombre}"

    printf "subjectAltName=%s\nextendedKeyUsage=serverAuth\nkeyUsage=digitalSignature,keyEncipherment\n" \
      "$san" > "${nombre}.ext"

    openssl x509 -req \
      -in "${nombre}.csr" \
      -CA ca.crt \
      -CAkey ca.key \
      -CAcreateserial \
      -out "${nombre}.crt" \
      -days 365 \
      -sha256 \
      -extfile "${nombre}.ext"
}

crear_certificado mongo "DNS:mongo,IP:127.0.0.1"
crear_certificado elasticsearch "DNS:elasticsearch,IP:127.0.0.1"
crear_certificado api "DNS:localhost,IP:127.0.0.1"

# MongoDB utiliza un PEM que contiene certificado y clave
cat mongo.crt mongo.key > mongo.pem

# Permisos de lectura para los contenedores del laboratorio
chmod 644 ca.crt mongo.pem
chmod 644 elasticsearch.key elasticsearch.crt
chmod 644 api.key api.crt

# La clave privada de la CA no se comparte con los contenedores
chmod 600 ca.key

echo "Certificados generados correctamente."
