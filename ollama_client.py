import json
import requests


class OllamaClient:

    def __init__(self, base_url, timeout=600):
        self.url = base_url.rstrip("/") + "/api/chat"
        self.timeout = timeout
        self.session = requests.Session()

    def chat(self, model, messages, temperature=0.7):

        response = self.session.post(
            self.url,
            json={
                "model": model,
                "messages": messages,
                "stream": True,
                "think": False,
                "options": {
                    "temperature": temperature
                }
            },
            stream=True,
            timeout=self.timeout
        )

        response.raise_for_status()

        try:
            for line in response.iter_lines(
                decode_unicode=True
            ):
                if not line:
                    continue

                yield json.loads(line)

        finally:
            response.close()