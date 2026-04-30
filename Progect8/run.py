import os
from dotenv import load_dotenv

# Load .env before importing app
env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(env_path)
print(f"Loaded .env from: {env_path}")

from backend.app import app

if __name__ == '__main__':
    app.run(debug=True)