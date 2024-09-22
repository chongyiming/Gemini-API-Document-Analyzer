import os
from dotenv import load_dotenv
import google.generativeai as genai
from PIL import Image
import PyPDF2

def process_images(image_dir='image_data'):
    images = []
    for file in os.listdir(image_dir):
        if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
            img_path = os.path.join(image_dir, file)
            images.append(Image.open(img_path))
    
    if not images:
        raise FileNotFoundError(f"No image files found in the {image_dir} directory.")
    return images

def process_file(file_path):
    _, extension = os.path.splitext(file_path)
    if extension.lower() == '.pdf':
        return process_pdf(file_path)
    else:
        return process_text(file_path)

def process_text(file_path):
    with open(file_path, 'r') as file:
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

# Configure genai with the API key
genai.configure(api_key=os.getenv('API_KEY'))

def main():
    file_type = input("Enter file type (image/file): ").lower()

    if file_type == "image":
        content = process_images()
    elif file_type == "file":
        file_data_dir = 'file_data'
        files = os.listdir(file_data_dir)
        if not files:
            raise FileNotFoundError(f"No files found in the {file_data_dir} directory.")
        file_path = os.path.join(file_data_dir, files[0])
        content = process_file(file_path)
    else:
        raise ValueError("Invalid file type. Please choose 'image' or 'file'.")

    model = genai.GenerativeModel("gemini-1.5-flash")
    user_prompt = input("Enter your prompt: ")
    
    if file_type == "image":
        response = model.generate_content([user_prompt] + content)
    else:
        response = model.generate_content([user_prompt, content])
    
    print(response.text)

if __name__ == "__main__":
    main()
