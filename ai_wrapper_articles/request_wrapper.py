import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

BEARER_TOKEN = os.getenv('OPEN_ROUTER_API_KEY')
MODEL = "openai/gpt-oss-120b:free" #"mistralai/mistral-small-3.1-24b-instruct:free"

def analyze_crypto_sentiment(article_text):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {BEARER_TOKEN}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a crypto market analyst. Your task is to analyze the provided article text "
                    "and determine its sentiment: POSITIVE, NEGATIVE, or NEUTRAL. "
                    "Return the result strictly as a JSON object with the following keys: "
                    "'sentiment' (string), 'score' (float 0-1), and 'reason' (brief explanation IN CZECH)."
                )
            },
            {
                "role": "user",
                "content": f"Analyze this article: {article_text}"
            }
        ],
        "response_format": { "type": "json_object" }
    }

    response = requests.post(url, headers=headers, data=json.dumps(payload))
    return response.json()

def parse_ai_response(raw_response):
    if 'error' in raw_response:
        print(f"API Error: {raw_response['error'].get('message')}")
        return None

    if 'choices' not in raw_response:
        print(f"Neočekávaný formát odpovědi: {raw_response}")
        return None

    try:
        content_str = raw_response['choices'][0]['message']['content']
        data = json.loads(content_str)
        
        return {
            "sentiment": data.get("sentiment"),
            "score": float(data.get("score", 0)),
            "reason": data.get("reason"),
            "model": raw_response.get("model"),
            "tokens_used": raw_response.get('usage', {}).get('total_tokens', 0)
        }
    except (json.JSONDecodeError, KeyError, IndexError) as e:
        print(f"Chyba při parsování obsahu: {e}")
        return None