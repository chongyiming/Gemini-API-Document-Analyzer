import os
from dotenv import load_dotenv
import google.generativeai as genai
from flask_cors import CORS
from flask import Flask, request, jsonify
app = Flask(__name__)
CORS(app, origins=["http://localhost:3000", "https://fkfyp.vercel.app"])

# Load environment variables from .env file
load_dotenv()

# Configure genai with the API key
genai.configure(api_key="AIzaSyArzJUTO2QAmt7vXedJWTHq5JxtmttoC0I")

# ======== API Endpoint ================
@app.route('/predict', methods=['POST'])
def predict():
    # Get the prompt from the request body
    data = request.get_json()
    if not data or 'prompt' not in data:
        return jsonify({'error': 'Prompt is required in the request body'}), 400

    user_prompt = data['prompt']

    model = genai.GenerativeModel("gemini-2.5-pro-preview-03-25")

    try:
        response = model.generate_content([user_prompt])
        return jsonify({
            'status': 'success',
            'response': response.text
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


# ========== Run App ====================
if __name__ == '__main__':
    app.run(debug=True)