#!/bin/bash

set -e

ES_URL="${ES_URL:-http://127.0.0.1:9200}"

echo "Esperando a Elasticsearch..."

READY=false

for i in $(seq 1 30); do
    if curl -fsS "$ES_URL" >/dev/null; then
        READY=true
        break
    fi

    sleep 2
done

if [ "$READY" != "true" ]; then
    echo "Error: Elasticsearch no esta disponible."
    exit 1
fi

echo "Elasticsearch disponible."

# Reinicializar el indice de pruebas
curl -sS -X DELETE "$ES_URL/articulos" >/dev/null || true

# Crear indice
curl -fsS -X PUT "$ES_URL/articulos" \
    -H "Content-Type: application/json" \
    -d '{
      "mappings": {
        "properties": {
          "title": {"type": "text"},
          "description": {"type": "text"}
        }
      }
    }'

# Insertar documentos
curl -fsS -X POST "$ES_URL/articulos/_bulk?refresh=true" \
    -H "Content-Type: application/x-ndjson" \
    --data-binary @- <<'NDJSON'
{"index":{"_id":"1"}}
{"title":"Teclado mecanico","description":"Teclado para ordenador"}
{"index":{"_id":"2"}}
{"title":"Raton inalambrico","description":"Raton Bluetooth"}
{"index":{"_id":"3"}}
{"title":"Monitor LED","description":"Pantalla para ordenador"}
NDJSON

echo ""
echo "Indice articulos inicializado correctamente."
