
#NOTE in V0 we were sending the whole conversation to the Model. The format was too huge and too prone
#to erros according to Claude. So We implemented a new version, that formats the answers in a 
#much escalable and light way:


import requests
import os
from dotenv import load_dotenv

load_dotenv()

chatting = True

def simple_agent(memory):

    # First, build a properly formatted conversation history
    formatted_conversation = ""
    # Loop through each item in memory and format it
    for item in memory:
        if "user" in item:
            # Add user message with proper markers
            formatted_conversation += f"<|im_start|>user\n{item['user']}<|im_end|>\n"
        elif "agent" in item:
            # Add agent response with proper markers
            formatted_conversation += f"<|im_start|>assistant\n{item['agent']}<|im_end|>\n"
    
    # Add the final marker for the model to continue
    formatted_conversation += "<|im_start|>assistant\n"

    api_token = os.getenv("HUGGINGFACE_API_TOKEN")
    model_id = os.getenv("DEFAULT_MODEL", "Qwen/Qwen2.5-Coder-32B-Instruct")
    api_url = f"https://api-inference.huggingface.co/models/{model_id}"
    headers = {"Authorization": f"Bearer {api_token}"}
    

    response = requests.post(
        api_url,
        headers=headers,
        json={"inputs": formatted_conversation, "parameters": {"max_new_tokens": 256}}
    )
    
    result = response.json()
    answer = result[0]["generated_text"].split("<|im_start|>assistant\n")[-1].split("<|im_end|>")[0]

    #print("\n" + formatted_conversation + "\n")
    return answer


memory = []

while chatting:

    question = input("You:\n")
    memory.append({"user" : question})

    response = simple_agent(memory)
    memory.append({"agent" : response})

    print(response + "\n")


    if question == "bye":
        chatting = False
