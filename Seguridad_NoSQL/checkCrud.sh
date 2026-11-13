echo "===== CREAR PEDIDO ====="
echo 

RESPUESTA=$(curl -sS -X POST http://127.0.0.1:8000/pedidos -H "Content-Type: application/json" -d '{"producto":"Libreta","cantidad":2}')

echo "$RESPUESTA"

echo 
ID=$(echo "$RESPUESTA" | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')

echo "ID: $ID"

echo
echo "===== CONSULTAR PEDIDOS ====="
echo 

curl -sS http://127.0.0.1:8000/pedidos

echo
echo -e "\n===== ACTUALIZAR PEDIDO ====="
echo 

curl -i -X PUT "http://127.0.0.1:8000/pedidos/$ID" -H "Content-Type: application/json" -d '{"producto":"Libreta actualizada","cantidad":5}'

echo 
echo -e "\n===== ELIMINAR PEDIDO ====="
echo 

curl -i -X DELETE "http://127.0.0.1:8000/pedidos/$ID"

echo
echo -e "\n===== COMPROBAR ELIMINACION ====="
echo 

curl -sS http://127.0.0.1:8000/pedidos

echo
