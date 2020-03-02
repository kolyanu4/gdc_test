from pathlib import Path

BASE_PATH = Path(__file__).resolve().parent

LOGLEVEL = 'DEBUG'
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(name)s - %(module)s:%(lineno)d  - %(message)s'

# NOTE: not a good practice but this is a codding assigment
SSH_USER = 'root'
SSH_PASSWORD = 'password'
