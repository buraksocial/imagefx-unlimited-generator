from flask import Flask, render_template, request, jsonify
import os
import requests
from dotenv import load_dotenv
import base64
import json

load_dotenv()

app = Flask(__name__)

SETTINGS_FILE = 'settings.json'

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_settings(settings):
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f)

def generate_image(prompt, image_count=4, seed=None):
    settings = load_settings()
    auth_token = settings.get('authToken') or os.getenv('IMAGEFX_AUTH_TOKEN')
    
    if not auth_token:
        return {"error": "Authentication token not found"}, 401

    if not auth_token.startswith("Bearer"):
        auth_token = f"Bearer {auth_token}"

    headers = {
        'accept': '*/*',
        'accept-language': 'en-US,en;q=0.9',
        'content-type': 'text/plain;charset=UTF-8',
        'dnt': '1',
        'origin': 'https://labs.google',
        'priority': 'u=1, i',
        'referer': 'https://labs.google/',
        'sec-ch-ua': '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Linux"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'cross-site',
        'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
        'authorization': auth_token
    }

    data = {
        "userInput": {
            "candidatesCount": image_count,
            "prompts": [prompt],
            "seed": seed,
        },
        "clientContext": {
            "sessionId": ";1740656431200",
            "tool": "IMAGE_FX"
        },
        "modelInput": {
            "modelNameType": "IMAGEN_3_1"
        },
        "aspectRatio": "IMAGE_ASPECT_RATIO_LANDSCAPE"
    }

    try:
        response = requests.post(
            "https://aisandbox-pa.googleapis.com/v1:runImageFx",
            headers=headers,
            json=data
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}, 500

@app.route('/')
def index():
    settings = load_settings()
    return render_template('index.html', default_count=settings.get('defaultCount', 4))

@app.route('/settings')
def settings_page():
    settings = load_settings()
    return render_template('settings.html', settings=settings)

@app.route('/api/settings', methods=['GET'])
def get_settings():
    settings = load_settings()
    # Don't send the full token in the response
    if 'authToken' in settings:
        settings['authToken'] = '********' if settings['authToken'] else ''
    return jsonify(settings)

@app.route('/api/settings', methods=['POST'])
def update_settings():
    try:
        data = request.get_json()
        settings = load_settings()
        
        if 'authToken' in data:
            settings['authToken'] = data['authToken']
        if 'defaultCount' in data:
            settings['defaultCount'] = data['defaultCount']
            
        save_settings(settings)
        return jsonify({"message": "Settings saved successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/generate', methods=['POST'])
def generate():
    data = request.get_json()
    prompt = data.get('prompt')
    count = int(data.get('count', 4))
    seed = data.get('seed')
    
    if not prompt:
        return jsonify({"error": "Prompt is required"}), 400

    result = generate_image(prompt, count, seed)
    if isinstance(result, tuple):
        return jsonify(result[0]), result[1]
    return jsonify(result)

@app.route('/api/generate', methods=['GET'])
def api_generate():
    try:
        # Get parameters from query string
        prompt = request.args.get('prompt')
        count = int(request.args.get('count', 4))
        seed = request.args.get('seed')
        
        if not prompt:
            return jsonify({"error": "Prompt is required"}), 400
            
        if count < 1 or count > 8:
            return jsonify({"error": "Count must be between 1 and 8"}), 400
            
        # Use the default auth token from settings
        settings = load_settings()
        auth_token = settings.get('authToken') or os.getenv('IMAGEFX_AUTH_TOKEN')
        
        if not auth_token:
            return jsonify({"error": "Authentication token not configured"}), 500

        if not auth_token.startswith("Bearer"):
            auth_token = f"Bearer {auth_token}"

        headers = {
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.9',
            'content-type': 'text/plain;charset=UTF-8',
            'dnt': '1',
            'origin': 'https://labs.google',
            'priority': 'u=1, i',
            'referer': 'https://labs.google/',
            'sec-ch-ua': '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Linux"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'cross-site',
            'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
            'authorization': auth_token
        }

        data = {
            "userInput": {
                "candidatesCount": count,
                "prompts": [prompt],
                "seed": int(seed) if seed else None,
            },
            "clientContext": {
                "sessionId": ";1740656431200",
                "tool": "IMAGE_FX"
            },
            "modelInput": {
                "modelNameType": "IMAGEN_3_1"
            },
            "aspectRatio": "IMAGE_ASPECT_RATIO_LANDSCAPE"
        }

        response = requests.post(
            "https://aisandbox-pa.googleapis.com/v1:runImageFx",
            headers=headers,
            json=data
        )
        response.raise_for_status()
        
        result = response.json()
        
        formatted_result = {
            "success": True,
            "images": []
        }
        
        for panel in result.get('imagePanels', []):
            for image in panel.get('generatedImages', []):
                formatted_result["images"].append({
                    "url": f"data:image/png;base64,{image['encodedImage']}",
                    "seed": image.get('seed'),
                    "prompt": prompt
                })
        
        return jsonify(formatted_result)
        
    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api')
def api_docs():
    return render_template('api.html')

@app.route('/api/test')
def api_test():
    return render_template('api_test.html')

if __name__ == '__main__':
    app.run(debug=True) 
