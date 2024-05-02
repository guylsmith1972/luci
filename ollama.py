import json
import requests
import subprocess

class OllamaService:
    _instance = None  # Singleton instance placeholder

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(OllamaService, cls).__new__(cls)
            cls.ollama_process = None  # Process placeholder
        return cls._instance
    
    @staticmethod
    def get_models(options):
        url = f"http://{options.host}:{options.port}/api/tags"
        
        try:
            response = requests.get(url)
            response.raise_for_status()  # This will raise an exception for HTTP errors
            data = response.json()
            models = data.get("models", [])
            return models
        except requests.RequestException as e:
            print(f"An error occurred: {e}")
            return None

    @staticmethod
    def is_model_installed(options):
        models = OllamaService.get_models(options)    
        
        target_parts = options.model.split(':')
        for model in models:
            model_parts = model.get("name").split(':')
            matches = True
            for i in range(len(target_parts)):
                if target_parts[i] != model_parts[i]:
                    matches = False
                    break
            if matches:
                return True
                
        return False
    
    @staticmethod
    def install_model(options, logger):
        url = f"http://{options.host}:{options.port}/api/pull"
        headers = {'Content-Type': 'application/json'}
        payload = {
            "name": options.install_model,
            "stream": False
        }

        try:
            logger.info(f'Installing Ollama model {options.install_model}')
            response = requests.post(url, headers=headers, data=json.dumps(payload))
            response.raise_for_status()  # Raises stored HTTPError, if one occurred.
            response_text = response.text
            response_json = json.loads(response_text)
            if response_json['status'] == 'success':
                return True  # Server indicates success.
            else:
                logger.critical(f'Ollama replied with failure message:\n\n{response_text}')
                return False  # Server response is not success, handle accordingly.
        except requests.RequestException as e:
            logger.critical(f'Failed to install model {options.model}: {str(e)}')
            return {'error': str(e)}  # Handle exceptions and return an error message.


    def query(self, prompt, options, logger):
        if self.ollama_process is None:
            self.start()
            
        if not OllamaService.is_model_installed(options):
            logger.critical(f'Model "{options.model}" is not installed. Rerun script with --install-model {options.model}')
            exit(0)

        url = f'http://{options.host}:{options.port}/api/generate'
        headers = {'Content-Type': 'application/json'}
        data = {'model': options.model, 'prompt': prompt, 'stream': False}
        try:
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            # Return just the text response from Ollama
            return response.json()['response']
        except requests.RequestException as e:
            return {'error': str(e)}

    def start(self):
        if self.ollama_process is None:
            self.ollama_process = subprocess.Popen(['ollama', 'serve'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def stop(self):
        if self.ollama_process:
            self.ollama_process.terminate()
            self.ollama_process.wait()
