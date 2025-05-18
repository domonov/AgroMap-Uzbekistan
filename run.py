import os
from app import create_app

# Get environment from FLASK_ENV or default to development
os.environ.setdefault('FLASK_ENV', 'development')
app = create_app()

if __name__ == "__main__":
    app.run()
