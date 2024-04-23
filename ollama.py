import requests
import subprocess


def query_llm(prompt):
    """
Queries the LLaMA Large Language Model using its API.

This function sends a POST request to the LLaMA API with the provided prompt
and retrieves the response from the model. The function returns the response
as JSON, which can be further processed by the caller.

Parameters:
prompt (str): The input text to query the language model with.

Returns:
dict: A dictionary containing the response from the LLaMA API.
       If an error occurs during the request, a dictionary with a single key-value pair 'error' will be returned.

Raises:
requests.RequestException: If there is an issue making the HTTP request to the API.
"""
    url = 'http://localhost:11434/api/generate'
    headers = {'Content-Type': 'application/json'}
    data = {'model': 'llama3', 'prompt': prompt, 'stream': False}
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()['response']
    except requests.RequestException as e:
        return {'error': str(e)}


def start():
    """
Starts the Ollama server as a background process.

This function runs the Ollama server in a separate process, allowing it to
run concurrently with other Python processes. The server is started using
the `ollama` command-line tool and its output is redirected to the Python
process's standard input/output streams.

Raises:
SubprocessError: If the Ollama server cannot be started or if an error
occurs while running the server.

Returns:
None: The function does not return any value. It starts the server as a
background process.
"""
    global ollama_process
    llama_process = subprocess.Popen(['ollama', 'serve'], stdout=subprocess
        .PIPE, stderr=subprocess.PIPE)


def stop():
    """
Stops an Ollama process, if one exists, and waits for it to complete.
This function checks if an Ollama process is running and terminates it
if so. It then waits until the process has finished executing before returning.
If no Ollama process is running, this function does nothing.

Raises:
None: This function does not raise any exceptions.

Returns:
None: The function does not return any value.
"""
    if ollama_process:
        ollama_process.terminate()
        ollama_process.wait()
