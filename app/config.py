from dotenv import load_dotenv
import os

load_dotenv()


class Config:
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    DB_PATH = os.path.abspath(os.path.join(BASE_DIR, "..", "leads.db"))
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{DB_PATH}?check_same_thread=False&_fk=1"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')

    LOG_FILE = os.path.abspath(os.path.join(BASE_DIR, "..", "logs", "app.log"))


config = Config()
