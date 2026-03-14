from request_wrapper import analyze_crypto_sentiment, parse_ai_response

clanek = "Krátká zpráva o kryptoměně Bitcoin..."
raw_data = analyze_crypto_sentiment(clanek)
print(raw_data)
clean_data = parse_ai_response(raw_data)

if clean_data:
    print(f"Ukládám do DB: {clean_data['sentiment']} ({clean_data['score']}) {clean_data}")
else:
    print("Analýza se nezdařila.")

"""
{'id': 'gen-1773508420-We2SDAnOVFhSEhwHcuZl', 'object': 'chat.completion', 'created': 1773508420, 'model': 'openai/gpt-oss-120b:free', 'provider': 'OpenInference', 'system_fingerprint': None, 'choices': [{'index': 0, 'logprobs': None, 'finish_reason': 'stop', 'native_finish_reason': 'stop', 'message': {'role': 'assistant', 'content': '{\n  "sentiment": "NEUTRAL",\n  "score": 0.5,\n  "reason": "Text pouze konstatuje fakt, že Bitcoin je kryptoměna, bez vyjádření kladného nebo záporného hodnocení."\n}', 'refusal': None, 'reasoning': 'We need to output JSON with sentiment, score, reason. The article is just "Bitcoin je kryptoměna" (Bitcoin is a cryptocurrency). That\'s neutral statement, no positive or negative sentiment. So sentiment NEUTRAL, score maybe 0.5? For neutral maybe 0.5. Provide reason.', 'reasoning_details': [{'type': 'reasoning.text', 'text': 'We need to output JSON with sentiment, score, reason. The article is just "Bitcoin je kryptoměna" (Bitcoin is a cryptocurrency). That\'s neutral statement, no positive or negative sentiment. So sentiment NEUTRAL, score maybe 0.5? For neutral maybe 0.5. Provide reason.', 'format': 'unknown', 'index': 0}]}}], 'usage': {'prompt_tokens': 168, 'completion_tokens': 131, 'total_tokens': 299, 'cost': 0, 'is_byok': False, 'prompt_tokens_details': {'cached_tokens': 0, 'cache_write_tokens': 0, 'audio_tokens': 0, 'video_tokens': 0}, 'cost_details': {'upstream_inference_cost': 0, 'upstream_inference_prompt_cost': 0, 'upstream_inference_completions_cost': 0}, 'completion_tokens_details': {'reasoning_tokens': 68, 'image_tokens': 0, 'audio_tokens': 0}}}
Ukládám do DB: NEUTRAL (0.5) {'sentiment': 'NEUTRAL', 'score': 0.5, 'reason': 'Text pouze konstatuje fakt, že Bitcoin je kryptoměna, bez vyjádření kladného nebo záporného hodnocení.', 'model': 'openai/gpt-oss-120b:free', 'tokens_used': 299}
"""