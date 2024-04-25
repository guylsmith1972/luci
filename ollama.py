import os
import requests
import subprocess

class OllamaService:
    _instance = None  # Singleton instance placeholder

    def __new__(cls):
        """Creates a new instance of the OllamaService class.
        This method uses Python's built-in `__new__` method to create a new instance
        of the class. It first checks if an instance already exists; if not, it
        creates a new one and initializes its attributes. The `ollama_process`
        attribute is set to None initially.
        Returns:
        OllamaService: A new instance of the OllamaService class."""
        if cls._instance is None:
            cls._instance = super(OllamaService, cls).__new__(cls)
            cls.ollama_process = None  # Process placeholder
        return cls._instance

    def query(self, prompt):
        """ Query the LLM process with a given prompt, starting the process if not already started.
        
        Parameters:
        self (object): The instance of the class to which this method belongs.
        prompt (str): The prompt that will be used to query the LLM process.
        
        Returns:
        dict: A dictionary containing the response from the LLM process. If an error occurs, a dictionary with an 'error' key is returned instead.
        
        Raises:
        None: This function does not raise any exceptions. It returns a dictionary in case of error."""
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
        """Starts the Ollama process if it is not already running.
        If the Ollama process is not currently running, this method will
        create a new process to run the 'ollama serve' command. If the process
        is already running, no action is taken. This method can be used to
        ensure that the Ollama server is always available when needed.
        
        Returns:
        None: The method does not return any value."""
        if self.ollama_process is None:
            self.ollama_process = subprocess.Popen(['ollama', 'serve'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def stop(self):
        """Stop the Ollama process if it is running.
         
        Stops the Ollama process, terminating its execution if it is currently running.
        If the process is already stopped or has finished executing, this method does nothing.
        Raises:
            None: This function does not raise any exceptions.
        Returns:
            None: The function does not return any value. It simply stops the Ollama process, if it exists.
        Example:
            >>> stop()
            # Stop the Ollama process if it is running.
        """
        if self.ollama_process:
            self.ollama_process.terminate()
            self.ollama_process.wait()
