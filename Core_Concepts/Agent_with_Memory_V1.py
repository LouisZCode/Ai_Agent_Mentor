
#NOTE in V0 we were sending the whole conversation to the Model.


import requests
import os
from dotenv import load_dotenv

load_dotenv()

chatting = True


def simple_agent(memory):
    api_token = os.getenv("HUGGINGFACE_API_TOKEN")
    model_id = os.getenv("DEFAULT_MODEL", "Qwen/Qwen2.5-Coder-32B-Instruct")
    api_url = f"https://api-inference.huggingface.co/models/{model_id}"
    headers = {"Authorization": f"Bearer {api_token}"}
    prompt = f"<|im_start|>user\n{memory}<|im_end|>\n<|im_start|>assistant\n"
    
    response = requests.post(
        api_url,
        headers=headers,
        json={"inputs": prompt, "parameters": {"max_new_tokens": 256}}
    )
    
    result = response.json()
    answer = result[0]["generated_text"].split("<|im_start|>assistant\n")[1]
    return answer

memory = []

while chatting:

    question = input("You:\n")
    memory.append({"user" : question})

    response = simple_agent(memory)
    print(response)
    memory.append({"agent" : response})

    print(memory)

    if question == "bye":
        chatting = False

