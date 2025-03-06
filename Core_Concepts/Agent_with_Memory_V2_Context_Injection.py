
#NOTE in V1 we added the correct formatting for memry in conversation, but what if we want to
#hive expertise or personality to our agent? here we will do a Context Injection, which is 
#basically a System Prompt that is given to the LLM mefore the conversation starts...

#NOTE I understand that """ X """ could be used, but looks like this varies on Model.. so lets
#use the Qwen way now, and adapt to later...


import requests
import os
from dotenv import load_dotenv

load_dotenv()

chatting = True

system_message = f"""<|im_start|>system
You are a bubbly and young AI agent with an enthusiastic personality.
You maintain a positive outlook on life.
You're also a passionate foodie who loves Mexican cuisine. In your responses,
naturally incorporate references to Mexican food.
Your food references should be creative - sometimes using comparisons, occasional rhymes,
or clever metaphors.
<|im_end|>"""


def simple_agent(memory):
    formatted_conversation = ""

    for item in memory:
        if "system" in item:
            formatted_conversation += system_message
        elif "user" in item:
            formatted_conversation += f"<|im_start|>user\n{item['user']}<|im_end|>\n"
        elif "agent" in item:
            formatted_conversation += f"<|im_start|>assistant\n{item['agent']}<|im_end|>\n"
    
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
    return answer


memory = []
memory.append({"system" : system_message})


while chatting:

    question = input("You:\n")
    memory.append({"user" : question})

    response = simple_agent(memory)
    memory.append({"agent" : response})

    print("\nAI:\n" + response + "\n")


    if question == "bye":
        chatting = False