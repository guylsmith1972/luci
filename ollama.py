import os
import requests
import subprocess

class OllamaService:
    _instance = None  # Singleton instance placeholder

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(OllamaService, cls).__new__(cls)
            cls.ollama_process = None  # Process placeholder
        return cls._instance

    def query(self, prompt):
        """ Query the LLM process with a given prompt, starting the process if not already started. """
        if self.ollama_process is None:
            self.start()

        url = 'http://localhost:11434/api/generate'
        headers = {'Content-Type': 'application/json'}
        data = {'model': 'llama3', 'prompt': prompt, 'stream': False}
        try:
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            return response.json()['response']
        except requests.RequestException as e:
            return {'error': str(e)}

    def start(self):
        """ Start the Ollama process if not already running. """
        if self.ollama_process is None:
            self.ollama_process = subprocess.Popen(['ollama', 'serve'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def stop(self):
        """ Stop the Ollama process if it is running. """
        if self.ollama_process:
            self.ollama_process.terminate()
            self.ollama_process.wait()
