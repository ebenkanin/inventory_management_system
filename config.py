from dotenv import load_dotenv
from datetime import timedelta
import os

load_dotenv('capstone.env')


class Config:
    SECRET_KEY = os.getenv('SECRET_KEY')
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=70)
    DB_PARAMETERS = {
        'host': os.getenv('HOSTNAME'),
        'database': os.getenv('DB_DATABASE'),
        'user': os.getenv('DB_USERNAME'),
        'password': os.getenv('PASSWORD'),
        'port': os.getenv('PORT')
    }


Debug = Config
print(Debug.DB_PARAMETERS)