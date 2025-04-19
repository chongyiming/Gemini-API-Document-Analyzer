import os
from dotenv import load_dotenv
import google.generativeai as genai
import PyPDF2
from supabase import create_client
import pandas as pd
from flask_cors import CORS
from flask import Flask, request, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
import atexit

app = Flask(__name__)
CORS(app, origins=["http://localhost:3000", "https://fkfyp.vercel.app"])


def process_file(file_path):
    _, extension = os.path.splitext(file_path)
    if extension.lower() == '.pdf':
        return process_pdf(file_path)
    else:
        return process_text(file_path)


def process_text(file_path):
    with open(file_path, 'r') as file:
        print(file.read())
        return file.read()


def process_pdf(file_path):
    with open(file_path, 'rb') as file:
        pdf_reader = PyPDF2.PdfReader(file)
        text = ''
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text


# Load environment variables from .env file
load_dotenv()

# Initialize Supabase client once at startup
url = os.getenv("SUPABASE_URL") or "https://onroqajvamgdrnrjnzzu.supabase.co"
key = os.getenv("SUPABASE_KEY") or "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9ucm9xYWp2YW1nZHJucmpuenp1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDEzNjExNTksImV4cCI6MjA1NjkzNzE1OX0.2_O9ufR4G5hrP0i_gXOkeSr5KNKvZgnV9gyKtF8s3oY"
supabase = create_client(url, key)

# Configure genai with the API key
genai.configure(api_key=os.getenv('API_KEY'))


# ======== API Endpoint ================
@app.route('/predict', methods=['POST'])
def predict():
    # Get the prompt from the request body
    data = request.get_json()
    if not data or 'prompt' not in data:
        return jsonify({'error': 'Prompt is required in the request body'}), 400

    user_prompt = data['prompt']

    file_data_dir = 'file_data'
    files = os.listdir(file_data_dir)
    if not files:
        return jsonify({'error': f'No files found in the {file_data_dir} directory.'}), 404

    file_path = os.path.join(file_data_dir, files[0])
    content = process_file(file_path)

    model = genai.GenerativeModel("gemini-2.5-pro-preview-03-25")

    try:
        response = model.generate_content([user_prompt, content])
        return jsonify({
            'status': 'success',
            'response': response.text
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


try:
    auth_response = supabase.auth.sign_in_with_password({
        "email": os.getenv("SUPABASE_EMAIL") or "chongyiming1205@gmail.com",
        "password": os.getenv("SUPABASE_PASSWORD") or "123456"
    })
    supabase.auth.session = auth_response.session
except Exception as auth_error:
    print(f"Failed to authenticate with Supabase: {auth_error}")
    # Handle authentication failure appropriately


def fetch_and_save_data():
    try:
        # Check if we have a valid session
        # Re-authenticate if session expired
        auth_response = supabase.auth.sign_in_with_password({
            "email": os.getenv("SUPABASE_EMAIL") or "chongyiming1205@gmail.com",
            "password": os.getenv("SUPABASE_PASSWORD") or "123456"
        })
        supabase.auth.session = auth_response.session

        response = (
            supabase
            .table("history")
            .select("created_at,norm_prob,mi_prob,class")
            .order("created_at", desc=True)
            .execute()
        )

        os.makedirs("file_data", exist_ok=True)
        pd.DataFrame(response.data).to_csv("file_data/history.csv", index=False)
        print(f"Data successfully updated")

    except Exception as e:
        print(f"Error in fetch_and_save_data: {str(e)}")
        # Consider adding retry logic or notification here


# Initialize scheduler
scheduler = BackgroundScheduler()
scheduler.add_job(
    fetch_and_save_data,
    'interval',
    seconds=60,
    max_instances=1,  # Prevent overlapping runs
    misfire_grace_time=30  # Allow some leeway
)
scheduler.start()

# Shutdown handler
atexit.register(lambda: scheduler.shutdown())

# ========== Run App ====================
if __name__ == '__main__':
    app.run(debug=True)

