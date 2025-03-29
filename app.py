from app import create_app
from flask_cors import CORS

app = create_app()
CORS(app, resources={r"/*": {"origins": "http://localhost:3000"}},supports_credentials=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)