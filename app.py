import os
import openai
from fastapi import FastAPI, Request, Form
from dotenv import load_dotenv
from twilio.twiml.voice_response import VoiceResponse
from twilio.rest import Client
import requests
import uvicorn

load_dotenv()  # Charger les variables d'environnement du fichier .env

app = FastAPI()

# Configurer les clés API depuis les variables d'environnement
twilio_account_sid = os.getenv('TWILIO_ACCOUNT_SID')
twilio_auth_token = os.getenv('TWILIO_AUTH_TOKEN')
twilio_phone_number = os.getenv('TWILIO_PHONE_NUMBER')
openai_api_key = os.getenv('OPENAI_API_KEY')
deepgram_api_key = os.getenv('DEEPGRAM_API_KEY')

# Configuration Twilio
twilio_client = Client(twilio_account_sid, twilio_auth_token)
openai.api_key = openai_api_key

@app.post("/voice")
async def voice():
    """Gérer les appels entrants avec Twilio."""
    response = VoiceResponse()
    response.say("Bonjour, comment puis-je vous aider ?", language="fr-FR")
    response.record(action='/recording', max_length=60, transcribe=False)
    return str(response)

@app.post("/recording")
async def recording(RecordingUrl: str = Form(...)):
    """Gérer l'enregistrement de la voix et générer une réponse."""
    # Étape 1 : Transcrire l'enregistrement avec Deepgram
    deepgram_url = "https://api.deepgram.com/v1/listen"
    headers = {
        'Authorization': f'Token {deepgram_api_key}',
        'Content-Type': 'application/json'
    }
    params = {
        "url": RecordingUrl,
        "punctuate": True,
    }

    response = requests.post(deepgram_url, json=params, headers=headers)
    response_data = response.json()

    if "results" not in response_data or len(response_data["results"]["channels"]) == 0:
        return {"error": "Erreur lors de la transcription de l'enregistrement"}

    transcript = response_data["results"]["channels"][0]["alternatives"][0]["transcript"]

    # Étape 2 : Générer une réponse avec OpenAI
    openai_response = openai.Completion.create(
        model="text-davinci-004",
        prompt=transcript,
        max_tokens=100
    )
    generated_response = openai_response.choices[0].text.strip()

    # Étape 3 : Lire la réponse à l'appelant
    twiml_response = VoiceResponse()
    twiml_response.say(generated_response, language="fr-FR")

    return str(twiml_response)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
