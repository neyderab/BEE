-- Esquema de la base de datos de BEE (PostgreSQL).
-- Es idempotente: se ejecuta al iniciar la aplicación y puede correrse varias
-- veces sin perder datos. También migra la tabla `usuarios` original.

CREATE TABLE IF NOT EXISTS universidades (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(120) NOT NULL UNIQUE,
    ciudad VARCHAR(60) NOT NULL
);

INSERT INTO universidades (nombre, ciudad) VALUES
    ('Universidad de San Buenaventura', 'Bogotá'),
    ('Universidad Nacional de Colombia', 'Bogotá'),
    ('Pontificia Universidad Javeriana', 'Bogotá'),
    ('Universidad de los Andes', 'Bogotá'),
    ('Universidad del Rosario', 'Bogotá')
ON CONFLICT (nombre) DO NOTHING;

CREATE TABLE IF NOT EXISTS usuarios (
    id SERIAL PRIMARY KEY,
    telefono VARCHAR(10) NOT NULL UNIQUE,
    nombre VARCHAR(50) NOT NULL DEFAULT '',
    apellido VARCHAR(50) NOT NULL DEFAULT '',
    rol VARCHAR(20) NOT NULL,
    universidad_id INTEGER REFERENCES universidades (id)
);

-- Migración de la tabla `usuarios` original (telefono, nombre, apellido, rol).
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS id SERIAL;
CREATE UNIQUE INDEX IF NOT EXISTS usuarios_id_idx ON usuarios (id);
ALTER TABLE usuarios
    ADD COLUMN IF NOT EXISTS universidad_id INTEGER REFERENCES universidades (id);

-- Una tienda pertenece a un usuario con rol "Tienda". Su universidad es la
-- del usuario que la administra.
CREATE TABLE IF NOT EXISTS tiendas (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER NOT NULL UNIQUE REFERENCES usuarios (id) ON DELETE CASCADE,
    nombre VARCHAR(80) NOT NULL
);

-- Un menú agrupa productos (por ejemplo: "Desayunos", "Bebidas").
CREATE TABLE IF NOT EXISTS menus (
    id SERIAL PRIMARY KEY,
    tienda_id INTEGER NOT NULL REFERENCES tiendas (id) ON DELETE CASCADE,
    nombre VARCHAR(60) NOT NULL
);

-- Los precios se guardan en pesos colombianos (enteros).
CREATE TABLE IF NOT EXISTS productos (
    id SERIAL PRIMARY KEY,
    menu_id INTEGER NOT NULL REFERENCES menus (id) ON DELETE CASCADE,
    nombre VARCHAR(80) NOT NULL,
    descripcion VARCHAR(200) NOT NULL DEFAULT '',
    precio INTEGER NOT NULL CHECK (precio > 0),
    disponible BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS pedidos (
    id SERIAL PRIMARY KEY,
    estudiante_id INTEGER NOT NULL REFERENCES usuarios (id) ON DELETE CASCADE,
    tienda_id INTEGER NOT NULL REFERENCES tiendas (id) ON DELETE CASCADE,
    estado VARCHAR(20) NOT NULL DEFAULT 'pendiente',
    hora_recogida TIME NOT NULL,
    total INTEGER NOT NULL CHECK (total > 0),
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Se guarda una copia del nombre y del precio para que el pedido no cambie
-- si la tienda edita o elimina el producto después.
CREATE TABLE IF NOT EXISTS pedido_items (
    id SERIAL PRIMARY KEY,
    pedido_id INTEGER NOT NULL REFERENCES pedidos (id) ON DELETE CASCADE,
    producto_id INTEGER REFERENCES productos (id) ON DELETE SET NULL,
    nombre_producto VARCHAR(80) NOT NULL,
    precio_unitario INTEGER NOT NULL,
    cantidad INTEGER NOT NULL CHECK (cantidad > 0)
);

CREATE INDEX IF NOT EXISTS pedidos_tienda_idx ON pedidos (tienda_id, estado);
CREATE INDEX IF NOT EXISTS pedidos_estudiante_idx ON pedidos (estudiante_id);
