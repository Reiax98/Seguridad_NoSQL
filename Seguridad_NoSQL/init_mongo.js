const tienda = db.getSiblingDB("tienda");

if (tienda.usuarios.countDocuments() === 0) {
    tienda.usuarios.insertMany([
        {
            username: "alice",
            password: "secreto123"
        },
        {
            username: "bob",
            password: "password456"
        }
    ]);
}

if (tienda.pedidos.countDocuments() === 0) {
    tienda.pedidos.insertMany([
        {
            producto: "Teclado",
            cantidad: 2
        },
        {
            producto: "Raton",
            cantidad: 3
        },
        {
            producto: "Monitor",
            cantidad: 1
        }
    ]);
}

print("Base de datos tienda inicializada correctamente");
