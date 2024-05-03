import json
import requests
import subprocess

class OllamaService:
    _instance = None  # Singleton instance placeholder

    def __new__(cls):
        """
        Creates or retrieves an instance of the OllamaService class.

        This special method ensures that only one instance of the OllamaService class
        can be created. If the class does not have an instance yet, it creates a new
        instance and assigns it to the class's `_instance` attribute. The method then
        returns this instance.

        Parameters:
        cls (class): The OllamaService class for which an instance is being created or
                    retrieved.

        Returns:
        object: An instance of the OllamaService class.

        Examples:
        Creates a new instance of the OllamaService class.   __new__(OllamaService)
        """
        if cls._instance is None:
            cls._instance = super(OllamaService, cls).__new__(cls)
            cls.ollama_process = None  # Process placeholder
        return cls._instance
    
    @staticmethod
    def get_models(options, logger):
        """
        Retrieves a list of models from a specified API endpoint.

        This static method sends an HTTP GET request to the provided API endpoint,
        parses the response as JSON, and returns the list of models. It handles any
        exceptions that occur during the request process by logging the error and
        returning None if the request fails.

        Parameters:
        options (object): An object containing host and port information for the API
                    endpoint.
        logger (object): A logger object used to log errors that occur during the
                    request process.

        Returns:
        list: A list of models retrieved from the API endpoint.

        Errors:
        requests.RequestException: Thrown if an error occurs during the HTTP request
                    process, such as a connection timeout or invalid response status
                    code.

        Examples:
        Retrieves models from API endpoint 'http://example.com:8080/api/tags' using
                    options and logger objects.   get_models({'host': 'example.com',
                    'port': 8080}, logger)
        """
        url = f"http://{options.host}:{options.port}/api/tags"
        
        try:
            response = requests.get(url)
            response.raise_for_status()  # This will raise an exception for HTTP errors
            data = response.json()
            models = data.get("models", [])
            return models
        except requests.RequestException as e:
            logger.error(f"An error occurred: {e}")
            return None

    @staticmethod
    def is_model_installed(options, logger):
        """
        Checks whether a specific model is installed in an OllamaService instance.

        This function takes options and logger as input, retrieves the list of installed
        models using the OllamaService API, and then checks if the target model matches
        any of the installed models based on their names. If a match is found, it
        returns True; otherwise, it returns False.

        Parameters:
        options (object): Contains configuration options that may affect the function's
                    behavior.
        logger (object): Represents a logging mechanism for recording events or errors.

        Returns:
        boolean: Indicates whether the target model is installed (True) or not (False).

        Examples:
        Checks if a specific model is installed using options and logger.
         is_model_installed(options, logger)
        """
        models = OllamaService.get_models(options, logger)    
        
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
        Installs a Ollama model using its API endpoint.

        This static method makes a POST request to the Ollama API to install a specified
        model. It handles both successful and failed installations, logging information
        and error messages accordingly.

        Parameters:
        options (object): An object containing options for installing the Ollama model,
                    such as host and port.
        logger (object): A logger object used to log information and error messages
                    during the installation process.

        Returns:
        boolean | dictionary: Returns a boolean indicating whether the installation was
                    successful, or a dictionary containing an error message if the
                    installation failed.

        Errors:
        requests.RequestException: Thrown if there is a network error during the request
                    to the Ollama API.

        Examples:
        Installs the 'my_model' model on host 'example.com' and port 8080, logging
                    installation information.   install_model({'host': 'example.com',
                    'port': 8080}, {'name': 'logger'})

        Notes:
        This method relies on the 'requests' library to make HTTP requests to the Ollama
         API.
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
        Queries the Ollama API with a given prompt and options.

        This function interacts with the Ollama API to generate text based on a provided
        prompt. It checks if an Ollama process is running, installs the required model
        if it's not already installed, and then sends a POST request to the API with the
        prompt and other necessary information. If an error occurs during the request,
        it returns an error message.

        Parameters:
        self (object): An instance of the class this function belongs to.
        prompt (string): The prompt used for generating text with Ollama.
        options (object): Options for the query, including model and host information.
        logger (object): A logger object for logging messages.

        Returns:
        string|dict: The generated text response from Ollama, or an error message if an
                    exception occurs.

        Errors:
        requests.RequestException: Thrown if there is a problem with the HTTP request to
                    the Ollama API.

        Examples:
        Queries the Ollama API with a prompt and options.   query(self, 'This is a test
                    prompt', {'model': 'my_model', 'host': 'localhost', 'port': 5000},
                    logger)

        Notes:
        This function relies on the `requests` library to send an HTTP request to the
         Ollama API. Ensure this library is installed for proper operation.
        """
        if self.ollama_process is None:
            self.start()
            
        if not OllamaService.is_model_installed(options, logger):
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
        Starts an Ollama process to serve requests.

        This method initializes or restarts the Ollama process if it's not already
        running. It creates a new subprocess for the 'ollama' command with 'serve' as
        its argument, and captures both stdout and stderr streams.

        Parameters:
        self (object): The object instance of the class this method is called on.

        Returns:
        void: Does not return any value. This method's primary effect is starting or
              restarting the Ollama process.

        Errors:
        RuntimeError: Thrown if there are issues creating or running the subprocess,
                    such as file system errors or invalid command arguments.

        Examples:
        Starts the Ollama process serving requests.   start()

        Notes:
        This method assumes that the 'ollama' command is installed and available on the
         system. If issues arise, it's recommended to check the subprocess creation or
         running status.
        """
        if self.ollama_process is None:
            self.ollama_process = subprocess.Popen(['ollama', 'serve'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def stop(self):
        """
        Stops an Ollama process, if one exists.

        This function checks if an Ollama process is running and terminates it if so. It
        then waits for the process to finish before returning.

        Parameters:
        self (object): The instance of the class containing this method.

        Returns:
        void: Does not return any value.

        Examples:
        Stops the Ollama process associated with an instance of a class.   stop()
        """
        if self.ollama_process:
            self.ollama_process.terminate()
            self.ollama_process.wait()
