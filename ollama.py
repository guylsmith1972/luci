import os
import requests
import subprocess

class OllamaService:
    _instance = None  # Singleton instance placeholder

    def __new__(cls):
        """
        Creates a new instance of an OllamaService class.
        This method ensures that only one instance of the service is created,
        and all subsequent requests to create a new instance will get the same
        previously created instance.

        Returns:
            The single instance of the OllamaService class.
        """
        if cls._instance is None:
            cls._instance = super(OllamaService, cls).__new__(cls)
            cls.ollama_process = None  # Process placeholder
        return cls._instance

    def query(self, prompt):
        """
        Queries the LLaMA model with a given prompt.
        This function sends a POST request to the LLaMA API with the provided prompt and
        returns the response from the API. If the API is not available, it will first
        start
        the process. The function handles exceptions and returns an error message if the
        request fails.

        Parameters:
        self (object): This object represents the current state of the query process.
        prompt (str): The input prompt to be queried by the LLaMA model.

        Returns:
        A JSON response from the LLaMA API, which includes the generated text or an
        error message. If the API request fails, it returns an error message with a
        description
        of the exception.

        Example:
        >>> query("What is AI?", self) # This will query the LLaMA model with the given
        prompt.
        Note: The function does not handle cases where the response from the API is None
        or an empty string. It is up to the caller to check for these conditions and
        decide how to handle them.
        """
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
        """
        Starts the Ollama server process.

        This function initializes the Ollama server by spawning a new process using the
        'ollama serve' command.

        Parameters:
        self (object): The instance of the class this method belongs to.

        Returns:
        None: This function does not return any value. It simply starts the Ollama
        server process.
        """
        if self.ollama_process is None:
            self.ollama_process = subprocess.Popen(['ollama', 'serve'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def stop(self):
        """
        Stops the Ollama process associated with this instance.
        This method terminates and waits for the Ollama process to complete, ensuring
        that any system resources it held are released.
        Raises:
        None: This method does not raise any exceptions.
        Returns:
        None: The method does not return any value. It modifies the state of this
        instance instead.
        Note:
        It is assumed that the Ollama process was started using a method like start() or
        run(), and that it is associated with this instance through an attribute like
        ollama_process.
        """
        if self.ollama_process:
            self.ollama_process.terminate()
            self.ollama_process.wait()
