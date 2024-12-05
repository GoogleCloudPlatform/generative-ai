import json
import os
from logicFunctions import *
from werkzeug.utils import secure_filename
from chromaWrapper import *
from flask import send_file, make_response
from marketingRag import *

import google.generativeai as genai
from flask import Flask, jsonify, request, send_file, send_from_directory
API_KEY = returnAPIKey()

genai.configure(api_key=API_KEY)

app = Flask(__name__, static_folder='frontend/dist')
app.config['UPLOAD_FOLDER'] = './uploads'
app.config['EXPORT_FOLDER'] = './export'

# Initialize Vertex AI
PROJECT_ID = "[your-project-id]" # Enter your project id here
LOCATION = "us-central1"  

marketing_client = marketingRag()
vertexai.init(project=PROJECT_ID, location=LOCATION)


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if path != "" and os.path.exists(app.static_folder + '/' + path):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')

# This should contain a POST request with a photo within
@app.route("/api/start_receiver", methods=["POST"])
def starter():
    if request.method == "POST":
        if 'file' not in request.files:
            return jsonify({ "error": "No file part!" })
        file = request.files['file']
        if file.filename == '':
            return jsonify({ "error": "No selected file" })
        if file and allowed_file(file.filename):
            filename = download_file(file)
            print( "File uploaded successfully")
    user_photo = upload_image_genai(filename)
    json_output = call_determiner(user_photo) # jsonify({ "data": json_output })
    data = json.loads(json_output)

    if not data["is_produce"]:
        return jsonify({ "no_produce": "Please resubmit with an image of produce!" })
    if data["more_than_one_produce"]:
        print("Proceed to Bulk Produce Analysis")
        bulk_output_json = bulk_selector_produce(data["produce_name"], user_photo)
        bulk_text_output = extract_bulk_text_from_json(bulk_output_json)
        editted_image_name = draw_box_image(bulk_output_json, filename, app.config['EXPORT_FOLDER'])
        return internal_image64(editted_image_name, data["produce_name"], "bulk_produce_selector", bulk_text_output)
    else:
        print("Proceed to Single Produce Analysis!")
        rating_json = rate_single_produce(data["produce_name"], user_photo)
        return jsonify({ "single_produce_rating": rating_json, "produce_name": data["produce_name"] })
    return jsonify({ "error": "Escaped starter function Logic!" })


# This should contain a POST request with the single_produce data packet within
# This will return a picture and text
@app.route("/api/request_marketing", methods=["POST"])
def marketing():
    if request.method == 'POST':
        produce_name = request.form.get('produce_name') # " Dragon Fruit"
        if produce_name is None:
            return "Produce Name not provided! Make sure to send the name packaged with the key: 'produce_name'", 400
        produce_review = request.form.get('produce_review') # {'rating': 1, 'quality_reasoning': "Was Moldy and wrinkled", 'pros': "Will add color to the trashcan", 'cons': "Clear signs of Mold and overripening"}
        produce_review_dict = json.loads(produce_review)
        # produce_review = {'rating': 1, 'quality_reasoning': "Was Moldy and wrinkled", 'pros': "Will add color to the trashcan", 'cons': "Clear signs of Mold and overripening"}
        if produce_review is None:
            return "Produce Review is not provided! Make sure to send the Key-Value pairs for ['Overall Rating' / 'Reasoning for Rating' / 'Pros' / 'Cons'] packaged with the key: 'produce_review'", 400
        try:
            global marketing_client
            marketing_llm_response = marketing_client.return_marketing_ad(produce_name, produce_review_dict) 
            # marketing_image = marketing_client.return_marketing_image(marketing_store_name)
            # marketing_llm_response = marketing_client.create_ad_text(data[produce_summary, data[pros], data[cons]) 
            return jsonify({'marketing': marketing_llm_response}), 200
        except Exception as e:
# Suggested code may be subject to a license. Learn more: ~LicenseLog:625310851.
            return jsonify({ "marketing error": str(e), "formData": produce_review_dict })


@app.route("/api/returnImage", methods=["POST"])
def return_image():
    if request.method == 'POST':
        filename = request.form.get('filename')
        if filename is None:
            return "Filename not provided!", 400

        image_path = os.path.join(app.config['EXPORT_FOLDER'], filename)
        if not os.path.isfile(image_path):
            return "Image not found", 404
        return send_from_directory(app.config['EXPORT_FOLDER'], filename)


@app.route("/api/returnImage64", methods=["POST"])
def return_image64():
    try:
        if request.method == 'POST':
            filename = request.form.get('filename')
            if filename is None:
                return "Filename not provided!", 400
            image_path = os.path.join(app.config['EXPORT_FOLDER'], filename)
            try:
                with open(image_path, "rb") as image_file:
                    encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
                    response = {
                        'message': "Here it is!",
                        'image': encoded_string
                    }
                    return jsonify(response)
            except Exception as e:
                return jsonify({'JSON Error': str(e)})
        return jsonify({'error': "Escaped /api/returnImage64 Logic"})
    except Exception as e:
        return jsonify({'Error': str(e)})



# Filename should be referring to a file within the 'export' folder
# Will return in JSON ready packet
def internal_image64(filename, produce_name, json_text_key = 'text', text_output = "Image returned!"):
    try:
        if filename is None:
            return jsonify({'error': "Filename not provided server-side!"}) 
        image_path = os.path.join(app.config['EXPORT_FOLDER'], filename)
        with open(image_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
            response = {
                json_text_key: text_output,
                'image' : encoded_string,
                'produce_name': produce_name
            }
            return jsonify(response)
        return jsonify({'error': "Escaped Logic"})
    except Exception as e:
        return jsonify({'error': str(e)})














def download_file(file):
    filename = secure_filename(file.filename)
    filename = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(filename)
    return filename

if __name__ == "__main__":
    app.run(port=int(os.environ.get('PORT', 8080)))
    # global ad_rag = create_rag_for_advertisment()

















@app.route("/api/uploadPhoto", methods=["POST"])
def upload():
    if request.method == "POST":
        if 'file' not in request.files:
            return "tes1"
            return jsonify({ "error": "No file part" })
        file = request.files['file']
        if file.filename == '':
            return "tes2"
            return jsonify({ "error": "No selected file" })
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filename = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filename)
            return "File uploaded successfully" 
        
    
        
        try:
            req_body = request.get_json()
            content = req_body.get("contents")
            model = genai.GenerativeModel(model_name=req_body.get("model"))
            response = model.generate_content(content, stream=True)
            def stream():
                for chunk in response:
                    yield 'data: %s\n\n' % json.dumps({ "text": chunk.text })

            return stream(), {'Content-Type': 'text/event-stream'}

        except Exception as e:
            return jsonify({ "error": str(e) })


@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('web', path)

@app.route('/detectImage', methods=['POST'])
def call_detetor(path):

    return ""


@app.route("/api/trialGenerate", methods=["POST"])
def trail_generate_api():
    if request.method == "POST":
        try:
            data = request.get_json()
            content = data.get("contents")
            model = genai.GenerativeModel(model_name=data.get("model"))
            response = model.generate_content(content)
            return jsonify({'response': response.text}), 200

        except Exception as e:
            return jsonify({ "error": str(e) })