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

-- ---------------------------------------------------------------------------
-- Tiempos de preparación, aceptación de pedidos, notificaciones y perfil.
-- ---------------------------------------------------------------------------

-- La tienda define en cuánto tiempo se puede recoger un pedido:
-- tiempo_min = 5 significa "de 5 a 10 minutos", 10 = "de 10 a 15", etc.
ALTER TABLE tiendas
    ADD COLUMN IF NOT EXISTS tiempo_min INTEGER NOT NULL DEFAULT 10
        CHECK (tiempo_min IN (5, 10, 15, 20, 25));
ALTER TABLE tiendas
    ADD COLUMN IF NOT EXISTS auto_aceptar BOOLEAN NOT NULL DEFAULT FALSE;

-- Ahora la hora de recogida la calcula la tienda (ya no la escribe el estudiante).
ALTER TABLE pedidos ALTER COLUMN hora_recogida DROP NOT NULL;
ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS tiempo_min INTEGER;
ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS tiempo_max INTEGER;
ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS aceptado_en TIMESTAMPTZ;

-- Si un estudiante cierra su cuenta, sus pedidos pasados se conservan en el
-- historial de la tienda (sin datos del estudiante).
ALTER TABLE pedidos ALTER COLUMN estudiante_id DROP NOT NULL;
ALTER TABLE pedidos DROP CONSTRAINT IF EXISTS pedidos_estudiante_id_fkey;
ALTER TABLE pedidos
    ADD CONSTRAINT pedidos_estudiante_id_fkey FOREIGN KEY (estudiante_id)
        REFERENCES usuarios (id) ON DELETE SET NULL;

-- Foto de perfil (JPEG de 256×256 generado por la aplicación).
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS foto BYTEA;
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS foto_actualizada TIMESTAMPTZ;

CREATE TABLE IF NOT EXISTS notificaciones (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER NOT NULL REFERENCES usuarios (id) ON DELETE CASCADE,
    pedido_id INTEGER REFERENCES pedidos (id) ON DELETE CASCADE,
    texto VARCHAR(200) NOT NULL,
    leida BOOLEAN NOT NULL DEFAULT FALSE,
    creada_en TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS notificaciones_usuario_idx
    ON notificaciones (usuario_id, leida, id DESC);

-- ---------------------------------------------------------------------------
-- Administradores y permisos.
-- ---------------------------------------------------------------------------

-- Una cuenta suspendida no puede iniciar sesión.
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS activo BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS creado_en TIMESTAMPTZ NOT NULL DEFAULT now();

-- Permisos de los usuarios con rol "Admin" (ver app/permisos.py).
CREATE TABLE IF NOT EXISTS permisos_usuario (
    usuario_id INTEGER NOT NULL REFERENCES usuarios (id) ON DELETE CASCADE,
    permiso VARCHAR(40) NOT NULL,
    PRIMARY KEY (usuario_id, permiso)
);

-- ---------------------------------------------------------------------------
-- Descripciones (se usan para generar docs/diccionario.html).
-- ---------------------------------------------------------------------------

COMMENT ON TABLE universidades IS 'Universidades donde funciona BEE.';
COMMENT ON COLUMN universidades.id IS 'Identificador de la universidad.';
COMMENT ON COLUMN universidades.nombre IS 'Nombre oficial; no se repite.';
COMMENT ON COLUMN universidades.ciudad IS 'Ciudad de la sede.';

COMMENT ON TABLE usuarios IS 'Personas que usan BEE: estudiantes, tiendas y administradores.';
COMMENT ON COLUMN usuarios.id IS 'Identificador del usuario.';
COMMENT ON COLUMN usuarios.telefono IS 'Celular de 10 dígitos con el que inicia sesión; no se repite.';
COMMENT ON COLUMN usuarios.nombre IS 'Nombre de la persona.';
COMMENT ON COLUMN usuarios.apellido IS 'Apellido de la persona.';
COMMENT ON COLUMN usuarios.rol IS 'Estudiante, Tienda o Admin.';
COMMENT ON COLUMN usuarios.universidad_id IS 'Universidad del estudiante o de la tienda (vacío para administradores).';
COMMENT ON COLUMN usuarios.foto IS 'Foto de perfil en JPEG de 256×256.';
COMMENT ON COLUMN usuarios.foto_actualizada IS 'Momento del último cambio de foto.';
COMMENT ON COLUMN usuarios.activo IS 'Falso si un administrador suspendió la cuenta.';
COMMENT ON COLUMN usuarios.creado_en IS 'Fecha de registro.';

COMMENT ON TABLE tiendas IS 'Tienda administrada por un usuario con rol Tienda.';
COMMENT ON COLUMN tiendas.id IS 'Identificador de la tienda.';
COMMENT ON COLUMN tiendas.usuario_id IS 'Usuario que administra la tienda (uno por tienda).';
COMMENT ON COLUMN tiendas.nombre IS 'Nombre que ven los estudiantes.';
COMMENT ON COLUMN tiendas.tiempo_min IS 'Minutos para recoger: 5 = de 5 a 10 min, ..., 25 = de 25 a 30 min.';
COMMENT ON COLUMN tiendas.auto_aceptar IS 'Si es verdadero, los pedidos nuevos se aceptan solos.';

COMMENT ON TABLE menus IS 'Secciones del menú de una tienda (Desayunos, Bebidas...).';
COMMENT ON COLUMN menus.id IS 'Identificador del menú.';
COMMENT ON COLUMN menus.tienda_id IS 'Tienda a la que pertenece.';
COMMENT ON COLUMN menus.nombre IS 'Nombre de la sección.';

COMMENT ON TABLE productos IS 'Productos que vende una tienda.';
COMMENT ON COLUMN productos.id IS 'Identificador del producto.';
COMMENT ON COLUMN productos.menu_id IS 'Menú donde aparece.';
COMMENT ON COLUMN productos.nombre IS 'Nombre del producto.';
COMMENT ON COLUMN productos.descripcion IS 'Descripción opcional.';
COMMENT ON COLUMN productos.precio IS 'Precio en pesos colombianos (mayor que cero).';
COMMENT ON COLUMN productos.disponible IS 'Falso si está agotado; no se puede pedir.';

COMMENT ON TABLE pedidos IS 'Pedidos que hacen los estudiantes a las tiendas de su universidad.';
COMMENT ON COLUMN pedidos.id IS 'Número del pedido.';
COMMENT ON COLUMN pedidos.estudiante_id IS 'Estudiante que pidió (vacío si cerró su cuenta).';
COMMENT ON COLUMN pedidos.tienda_id IS 'Tienda que recibe el pedido.';
COMMENT ON COLUMN pedidos.estado IS 'pendiente, aceptado, preparando, listo, entregado o cancelado.';
COMMENT ON COLUMN pedidos.hora_recogida IS 'Hora elegida por el estudiante (solo pedidos de la primera versión).';
COMMENT ON COLUMN pedidos.total IS 'Total en pesos colombianos.';
COMMENT ON COLUMN pedidos.creado_en IS 'Momento en que se hizo el pedido.';
COMMENT ON COLUMN pedidos.tiempo_min IS 'Minutos mínimos para recoger, copiados de la tienda al pedir.';
COMMENT ON COLUMN pedidos.tiempo_max IS 'Minutos máximos para recoger, copiados de la tienda al pedir.';
COMMENT ON COLUMN pedidos.aceptado_en IS 'Momento en que la tienda aceptó; desde ahí corre el tiempo.';

COMMENT ON TABLE pedido_items IS 'Productos de cada pedido.';
COMMENT ON COLUMN pedido_items.id IS 'Identificador de la línea.';
COMMENT ON COLUMN pedido_items.pedido_id IS 'Pedido al que pertenece.';
COMMENT ON COLUMN pedido_items.producto_id IS 'Producto pedido (vacío si la tienda lo borró).';
COMMENT ON COLUMN pedido_items.nombre_producto IS 'Nombre del producto al momento de pedir.';
COMMENT ON COLUMN pedido_items.precio_unitario IS 'Precio al momento de pedir.';
COMMENT ON COLUMN pedido_items.cantidad IS 'Unidades pedidas (mayor que cero).';

COMMENT ON TABLE notificaciones IS 'Avisos de la campana sobre los pedidos.';
COMMENT ON COLUMN notificaciones.id IS 'Identificador de la notificación.';
COMMENT ON COLUMN notificaciones.usuario_id IS 'Usuario que la recibe.';
COMMENT ON COLUMN notificaciones.pedido_id IS 'Pedido al que se refiere.';
COMMENT ON COLUMN notificaciones.texto IS 'Mensaje que se muestra.';
COMMENT ON COLUMN notificaciones.leida IS 'Verdadero cuando el usuario abrió la campana.';
COMMENT ON COLUMN notificaciones.creada_en IS 'Momento en que se creó.';

COMMENT ON TABLE permisos_usuario IS 'Permisos de cada administrador.';
COMMENT ON COLUMN permisos_usuario.usuario_id IS 'Administrador que tiene el permiso.';
COMMENT ON COLUMN permisos_usuario.permiso IS 'Clave del permiso (ver app/permisos.py).';
