import os
from fastapi import FastAPI, Request
from twilio.twiml.voice_response import VoiceResponse
from twilio.rest import Client
from openai import OpenAI
import openai
from pydub import AudioSegment
import requests
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

app = FastAPI()

# Configuration de l'API OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

# Configuration de l'API Twilio
twilio_account_sid = os.getenv("TWILIO_ACCOUNT_SID")
twilio_auth_token = os.getenv("TWILIO_AUTH_TOKEN")
twilio_client = Client(twilio_account_sid, twilio_auth_token)

@app.post("/twilio/voice")
async def handle_call(request: Request):
    """Gère l'appel Twilio"""
    twiml_response = VoiceResponse()
    twiml_response.say("Bonjour, comment puis-je vous aider ?")

    # Enregistrer la réponse de l'appelant
    twiml_response.record(
        action="/twilio/recording",
        recording_status_callback="/twilio/recording-status",
        max_length=60,
        transcribe=False,
    )
    return Response(content=str(twiml_response), media_type="application/xml")

@app.post("/twilio/recording")
async def handle_recording(request: Request):
    """Gère l'enregistrement audio et génère une réponse"""
    form_data = await request.form()
    recording_url = form_data["RecordingUrl"]

    # Télécharger l'enregistrement
    response = requests.get(recording_url)
    audio = AudioSegment.from_file(io.BytesIO(response.content), format="wav")

    # Convertir l'audio en texte (GPT-4 ou autre)
    transcription = openai.Audio.transcribe("whisper-1", audio.raw_data)

    # Générer une réponse avec GPT-4
    response_gpt = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": transcription}],
    )
    generated_text = response_gpt.choices[0].message["content"].strip()

    # Convertir le texte en audio avec TTS
    tts_response = openai.Audio.create(
        engine="text-to-speech",
        text=generated_text,
        voice="fr-realistic"
    )

    # Créer une réponse TwiML pour lire l'audio synthétisé
    twiml_response = VoiceResponse()
    twiml_response.play(tts_response["url"])

    return Response(content=str(twiml_response), media_type="application/xml")

# Lancer le serveur avec Uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
