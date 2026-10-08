import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

conexion = mysql.connector.connect(
    host=os.getenv("DB_HOST"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    database=os.getenv("DB_NAME")
)

print("Conexión exitosa a Bee_db1")

conexion.close()