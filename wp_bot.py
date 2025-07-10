import os
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import requests
import tempfile
import os
from dotenv import load_dotenv
load_dotenv()


app = Flask(__name__)

# Your DocDynamo endpoint
DOC_API_URL = os.getenv("DOC_API_URL")

# Twilio credentials (from your console)
TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_AUTH = os.getenv("TWILIO_AUTH")

# Store user files in memory for simplicity
user_files = {}

@app.route('/whatsapp', methods=['POST'])
def whatsapp():
    sender = request.values.get('From')
    msg_body = request.values.get('Body', '').strip()
    num_media = int(request.values.get('NumMedia', 0))

    resp = MessagingResponse()

    # Handle file upload
    if num_media > 0:
        media_url = request.values.get('MediaUrl0')
        media_type = request.values.get('MediaContentType0')

        if 'pdf' in media_type or 'docx' in media_type:
            file_ext = ".pdf" if 'pdf' in media_type else ".docx"

            # ✅ Use Twilio credentials to access the file
            response = requests.get(media_url, auth=(TWILIO_SID, TWILIO_AUTH))

            if response.ok:
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=file_ext)
                temp_file.write(response.content)
                temp_file.close()

                user_files[sender] = temp_file.name

                resp.message(
                    "✅ Document received!\n\nNow ask your question like:\n"
                    "*Act as Student: What is the summary?*"
                )
            else:
                resp.message("⚠️ Failed to download the document. Auth issue. Please try again.")
        else:
            resp.message("⚠️ Only PDF or DOCX files are supported.")
        return str(resp)

    # Handle persona + question message
    elif msg_body.lower().startswith("act as"):
        if sender not in user_files:
            resp.message("📄 Please upload a PDF or DOCX file first.")
            return str(resp)

        try:
            persona_part, question = msg_body.split(":", 1)
            persona = persona_part.replace("Act as", "").strip()
            question = question.strip()

            with open(user_files[sender], 'rb') as f:
                files = {'docs': (os.path.basename(f.name), f)}
                data = {'question': question, 'persona': persona}
                r = requests.post(DOC_API_URL, data=data, files=files)

            if r.ok:
                json_res = r.json()
                answer = json_res.get("response", "Couldn’t process the document.")
            else:
                answer = "❌ DocDynamo backend failed."

        except Exception as e:
            answer = f"❌ Error: {str(e)}"

        resp.message(answer)
        return str(resp)

    # Default welcome message
    else:
        resp.message(
            "👋 Welcome to DocDynamo on WhatsApp!\n\n"
            "Step 1: Upload a PDF or DOCX\n"
            "Step 2: Ask your question like:\n"
            "*Act as Student: What is the summary?*"
        )
        return str(resp)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

