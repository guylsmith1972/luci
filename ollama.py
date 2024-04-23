import requests
import subprocess


def query_llm(prompt):
    url = 'http://localhost:11434/api/generate'
    headers = {'Content-Type': 'application/json'}
    data = {
        "model": "llama3",
        "prompt": prompt,
        "stream": False
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()['response']
    except requests.RequestException as e:
        return {"error": str(e)}


def start():
    global ollama_process
    # Start the ollama server as a background process
    llama_process = subprocess.Popen(["ollama", "serve"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def stop():
    if ollama_process:
        ollama_process.terminate()  # Terminate the subprocess
        ollama_process.wait()       # Wait for the process to terminate
