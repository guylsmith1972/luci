import json
import requests
import subprocess

class OllamaService:
    _instance = None  # Singleton instance placeholder

    def __new__(cls):
        """
        Singleton pattern implementation.
        This method creates a single instance of the OllamaService class and returns it.

        Returns:
            The single instance of the OllamaService class.
        """
        if cls._instance is None:
            cls._instance = super(OllamaService, cls).__new__(cls)
            cls.ollama_process = None  # Process placeholder
        return cls._instance
    
    @staticmethod
    def get_models(options):
        """
        Retrieves a list of available machine learning models from a specified API
        endpoint.

        This function sends a GET request to the provided URL, parses the response JSON,
        and returns the list of models. If an error occurs during the request or
        parsing,
        it prints the error message and returns None instead.

        Parameters:
          options (dict): A dictionary containing the host and port details for
                          the API endpoint.

        Returns:
          list: A list of available machine learning models, or None if an error
                occurred.
        """
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
        """
        Determines whether the specified model is installed.

        This function checks if a specific model is available by comparing its parts
        against the list of models provided by OllamaService. The model name and its
        parts are split using the colon (:) character.

        Parameters:
          options (dict): A dictionary containing information about the model to check,
                          including its name and any other relevant details.

        Returns:
          bool: True if the specified model is installed, False otherwise.
        """
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
        """
        Installs a Ollama model using the provided options and logger.

        This method sends a POST request to the specified API endpoint with the required
        payload
        and checks the response. If the installation is successful, it returns True;
        otherwise,
        it logs a critical error message and returns False.

        If any exceptions occur during the process, such as network errors or invalid
        responses,
        the method logs a critical error message and returns an error dictionary
        containing
        the exception message.

        Parameters:
          options (dict): Options for installing the model.
          logger (Logger): Logger object to log installation status.

        Returns:
          bool: True if installation is successful, False otherwise.
          dict: Error dictionary with the exception message if an error occurs.
        """
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
        """
        Queries the OLLAMA service with the provided prompt and options.

        This function sends a POST request to the OLLAMA API with the specified model,
        prompt, and options. If the model is not installed, it will log an error message
        and exit. It also handles any exceptions that occur during the request and
        returns the response as JSON.

        Parameters:
          self (object): The instance of the class.
          prompt (str): The text prompt to query OLLAMA with.
          options (dict): A dictionary containing the model, host, port, and other
                          configuration options for the OLLAMA service.
          logger (logger): A logging object used for logging errors.

        Returns:
          dict: A JSON response from OLLAMA. If an error occurs during the request,
                it will return a dictionary with an "error" key containing the error
                message.
        """
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
        """
        Starts the Ollama process in the background.
        This method initializes and runs the Ollama server as a separate
        process. If the process has not been started yet, it creates a new Popen
        object to manage the process.

        Parameters:
          self (Ollama): The instance of the Ollama class that this method is part of.

        Returns:
          None: This method does not return any value.
        """
        if self.ollama_process is None:
            self.ollama_process = subprocess.Popen(['ollama', 'serve'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def stop(self):
        """
        Stops an Ollama process, if one is running.

        This method terminates and waits for the Ollama process to finish. It should be
        called when you are done using the Ollama process.
        """
        if self.ollama_process:
            self.ollama_process.terminate()
            self.ollama_process.wait()
