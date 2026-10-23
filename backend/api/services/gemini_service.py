import httpx
from api.config import get_settings
class GeminiNotConfiguredError(Exception): pass
class GeminiUpstreamError(Exception): pass
async def generate_text(system_prompt, user_prompt, *, max_output_tokens=512, temperature=0.2):
 s=get_settings(); key=s.GEMINI_API_KEY
 if not key: raise GeminiNotConfiguredError()
 url=f'https://generativelanguage.googleapis.com/v1beta/models/{s.GEMINI_MODEL}:generateContent'
 body={'system_instruction':{'parts':[{'text':system_prompt}]},'contents':[{'role':'user','parts':[{'text':user_prompt}]}],'generationConfig':{'maxOutputTokens':max_output_tokens,'temperature':temperature}}
 try:
  async with httpx.AsyncClient(timeout=30) as c: r=await c.post(url,json=body,headers={'x-goog-api-key':key})
 except Exception as e: raise GeminiUpstreamError('Gemini request failed') from e
 if r.status_code>=400: raise GeminiUpstreamError(f'Gemini upstream returned HTTP {r.status_code}')
 try: text=r.json()['candidates'][0]['content']['parts'][0]['text']
 except Exception as e: raise GeminiUpstreamError('Gemini returned no usable text') from e
 if not text: raise GeminiUpstreamError('Gemini returned no usable text')
 return text
