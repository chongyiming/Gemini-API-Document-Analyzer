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
from io import BytesIO
import tempfile
app = Flask(__name__)
CORS(app, origins=["http://localhost:3000", "https://fkfyp.vercel.app"])

# Load environment variables from .env file
load_dotenv()

# Initialize Supabase client once at startup
url = os.getenv("SUPABASE_URL") or "https://onroqajvamgdrnrjnzzu.supabase.co"
key = os.getenv(
    "SUPABASE_KEY") or "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9ucm9xYWp2YW1nZHJucmpuenp1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDEzNjExNTksImV4cCI6MjA1NjkzNzE1OX0.2_O9ufR4G5hrP0i_gXOkeSr5KNKvZgnV9gyKtF8s3oY"
supabase = create_client(url, key)

# Configure genai with the API key
genai.configure(api_key=os.getenv('API_KEY'))


def process_file_content(file_content, file_name):
    _, extension = os.path.splitext(file_name)
    if extension.lower() == '.pdf':
        return process_pdf(file_content)
    else:
        return process_text(file_content)


def process_text(file_content):
    return file_content.decode('utf-8')


def process_pdf(file_content):
    pdf_reader = PyPDF2.PdfReader(BytesIO(file_content))
    text = ''
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text


def get_latest_file_from_storage():
    try:
        # List all files in the storage bucket
        files = supabase.storage.from_('file').list()
        if not files:
            return None, None

        # Sort files by created_at (assuming the name includes timestamp or we have metadata)
        # Here we'll just get the first file for simplicity
        # In production, you might want to implement proper sorting
        file_name = "history.csv"

        # Download the file
        file_content = supabase.storage.from_('file').download(file_name)
        return file_content, file_name

    except Exception as e:
        print(f"Error getting file from storage: {str(e)}")
        return None, None


# ======== API Endpoint ================
@app.route('/predict', methods=['POST'])
def predict():
    # Get the prompt from the request body
    data = request.get_json()
    if not data or 'prompt' not in data:
        return jsonify({'error': 'Prompt is required in the request body'}), 400

    user_prompt = data['prompt']+",response should be without *,\n\n and \t"

    # Get file from Supabase storage
    file_content, file_name = get_latest_file_from_storage()
    if not file_content:
        return jsonify({'error': 'No files found in storage.'}), 404

    content = process_file_content(file_content, file_name)

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


def authenticate_supabase():
    try:
        auth_response = supabase.auth.sign_in_with_password({
            "email": os.getenv("SUPABASE_EMAIL") or "chongyiming1205@gmail.com",
            "password": os.getenv("SUPABASE_PASSWORD") or "123456"
        })
        supabase.auth.session = auth_response.session
        return True
    except Exception as auth_error:
        print(f"Failed to authenticate with Supabase: {auth_error}")
        return False


def fetch_and_save_data():
    try:
        # Re-authenticate if needed
        if not authenticate_supabase():
            return

        response = (
            supabase
            .table("history")
            .select("created_at,norm_prob,mi_prob,class")
            .order("created_at", desc=True)
            .execute()
        )

        # Create a temporary file
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as tmp:
            df = pd.DataFrame(response.data)
            df.to_csv(tmp.name, index=False)

            # Upload the temporary file
            with open(tmp.name, 'rb') as f:
                supabase.storage.from_('file').upload(
                    'history.csv',
                    f,
                    {'content-type': 'text/csv', 'upsert': 'true'}
                )

        # Clean up the temporary file
        os.unlink(tmp.name)
        print("Data successfully updated in Supabase storage")

    except Exception as e:
        print(f"Error in fetch_and_save_data: {str(e)}")
        if 'tmp' in locals() and os.path.exists(tmp.name):
            os.unlink(tmp.name)

# Initialize scheduler
scheduler = BackgroundScheduler()
scheduler.add_job(
    func=fetch_and_save_data,
    trigger='interval',
    seconds=60,
    max_instances=1,
    misfire_grace_time=30
)
scheduler.start()

# Shutdown handler
atexit.register(lambda: scheduler.shutdown())

# ========== Run App ====================
if __name__ == '__main__':
    app.run(debug=True)