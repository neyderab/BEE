"""CONTROLADOR (la C de MVC): rutas HTTP de Bee.

Cada módulo es un router de FastAPI. Un controlador recibe la petición,
valida lo que escribió el usuario, le pide al modelo (app.modelos) que lea o
cambie los datos y elige qué vista (plantilla) mostrar. No contiene SQL.
"""
