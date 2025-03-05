# Import what we need
import requests
import os
from dotenv import load_dotenv

load_dotenv()

def simple_agent(question):
    api_token = os.getenv("HUGGINGFACE_API_TOKEN")
    model_id = os.getenv("DEFAULT_MODEL", "Qwen/Qwen2.5-Coder-32B-Instruct")
    api_url = f"https://api-inference.huggingface.co/models/{model_id}"
    headers = {"Authorization": f"Bearer {api_token}"}
    prompt = f"<|im_start|>user\n{question}<|im_end|>\n<|im_start|>assistant\n"
    
    response = requests.post(
        api_url,
        headers=headers,
        json={"inputs": prompt, "parameters": {"max_new_tokens": 256}}
    )
    
    result = response.json()
    answer = result[0]["generated_text"].split("<|im_start|>assistant\n")[1]
    return answer



question = input("Ask a question to the agent:\n")
response = simple_agent(question)
print(response)