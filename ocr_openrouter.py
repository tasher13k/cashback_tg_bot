from openai import OpenAI
import base64

class CashbackAnalyzer:
    def __init__(self, key):
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=key,
        )
    
    async def say_something(self):

        response = self.client.chat.completions.create(
            model="nvidia/nemotron-nano-12b-v2-vl:free",
            messages=[
                {
                    "role": "user",
                    "content": "Answer using less than 10 words: is the Sun bigger than the Earth?"
                }
            ],
            extra_body={"reasoning": {"enabled": False}}
        )
        return response.choices[0].message.content

    async def analyze_screenshot(self, image_bytes: bytes):
        
        """Анализирует скриншот и возвращает условия кэшбэка"""
        
        # Кодируем изображение
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        
        # Определяем MIME тип автоматически
        mime_type = self._detect_mime_type(image_bytes)
        
        prompt = """
        You analyze a screenshot of a banking application (Sberbank, T-bank, Alfa-Bank, VTB) to extract cashback categories. Find all cashback categories and the corresponding percentages. Return only the "category percentage" pairs (without the % sign). Critical rules: save the original category names literally as in the screenshot. Don't paraphrase, don't shorten, don't translate the names.
        """

        response = self.client.chat.completions.create(
            model="nvidia/nemotron-nano-12b-v2-vl:free",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            extra_body={"reasoning": {"enabled": True}},
            #max_tokens=1000,
            #temperature=0.1  # Для более точных ответов
        )

        return response.choices[0].message.content
        
        # Парсим JSON ответ
        try:
            result = response.choices[0].message
            return result
        except json.JSONDecodeError:
            # Если модель вернула не JSON, пытаемся извлечь структурированные данные
            return self._extract_from_text(response.choices[0].message.content)
    
    def _detect_mime_type(self, image_bytes: bytes) -> str:
        """Определяет MIME тип по первым байтам"""
        if image_bytes.startswith(b'\xff\xd8\xff'):
            return "image/jpeg"
        elif image_bytes.startswith(b'\x89PNG\r\n\x1a\n'):
            return "image/png"
        elif image_bytes.startswith(b'RIFF') and image_bytes[8:12] == b'WEBP':
            return "image/webp"
        else:
            return "image/jpeg"  # fallback


'''
# Preserve the assistant message with reasoning_details
messages = [
  {"role": "user", "content": "How many r's are in the word 'strawberry'?"},
  {
    "role": "assistant",
    "content": response.content,
    "reasoning_details": response.reasoning_details  # Pass back unmodified
  },
  {"role": "user", "content": "Are you sure? Think carefully."}
]

# Second API call - model continues reasoning from where it left off
response2 = client.chat.completions.create(
  model="nvidia/nemotron-nano-12b-v2-vl:free",
  messages=messages,
  extra_body={"reasoning": {"enabled": True}}
)
'''