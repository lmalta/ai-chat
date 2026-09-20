import json
import requests
import threading


class OllamaClient:

    def __init__(self, base_url, timeout=600):
        self.url = base_url.rstrip("/") + "/api/chat"
        self.timeout = timeout
        self.session = requests.Session()

        self._lock = threading.Lock()
        self._active_response = None
        self._cancel_event = threading.Event()

    def chat(self, model, messages, temperature=0.7):

        self._cancel_event.clear()

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

        with self._lock:
            self._active_response = response

        try:
            for line in response.iter_lines(
                decode_unicode=True
            ):
                if self._cancel_event.is_set():
                    print("[OLLAMA] Annulation détectée")
                    break

                if not line:
                    continue

                yield json.loads(line)

        finally:
            response.close()

            with self._lock:
                if self._active_response is response:
                    self._active_response = None

            self._cancel_event.clear()

    def cancel(self):
        with self._lock:
            response = self._active_response

        if response is not None:
            print("[OLLAMA] Demande d'annulation")
            self._cancel_event.set()
            return True

        print("[OLLAMA] Aucune génération active")
        return False