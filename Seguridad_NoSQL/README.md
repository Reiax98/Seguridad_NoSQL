# Laboratorio de Seguridad NoSQL

## Requisitos

- Linux
- Docker Engine
- Docker Compose
- Python 3.11
- curl

## Estructura

- docker-compose.yml: configuracion de los servicios.
- init_mongo.js: inicializacion de MongoDB.
- fastapi-app/: aplicacion FastAPI.
- scripts/init_elastic.sh: inicializacion de Elasticsearch.

## Inicio

Desde el directorio principal:

    docker compose -p nosql-baseline up -d --build

## Comprobar servicios

    docker compose -p nosql-baseline ps

## Inicializar Elasticsearch

    ./scripts/init_elastic.sh

## Comprobar API

    curl http://127.0.0.1:8000/health

## Detener servicios

    docker compose -p nosql-baseline down

## Seguridad

Este laboratorio utiliza configuraciones vulnerables
deliberadamente. Debe ejecutarse exclusivamente en
un entorno local y con datos ficticios.
