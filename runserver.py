"""
This script runs the FlaskWebStudentApp application using a development server.
"""

from os import environ
from FlaskWebStudentApp import app

if __name__ == '__main__':
    HOST = environ.get('SERVER_HOST', 'localhost')
    try:
        PORT = int(environ.get('SERVER_PORT', '5555'))
    except ValueError:
        PORT = 5555
    
    app.secret_key = 'your_secret_keyfffff'
    app.run("0.0.0.0", 25565)
