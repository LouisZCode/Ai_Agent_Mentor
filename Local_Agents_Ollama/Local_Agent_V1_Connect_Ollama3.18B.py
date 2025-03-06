#NOTE - I wanted to add a while loop to continue the conversation with my local DeepSeek model.
#Also, I want for now to take away the thniking part, so I can focus on the result sof the
#conversation. We can add the thinking part later

#NOTE - Maybe also good idea to have anothe rModel just in case?


chatting = True
import requests

system_message = f"""<|im_start|>system
Provide direct answers without showing your reasoning process
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
            formatted_conversation += item["system"]  # Use value from dictionary
        elif "user" in item:
            formatted_conversation += f"<|im_start|>user\n{item['user']}<|im_end|>\n"
        elif "agent" in item:
            formatted_conversation += f"<|im_start|>assistant\n{item['agent']}<|im_end|>\n"

    formatted_conversation += "<|im_start|>assistant\n"

    # Model name should match exactly as shown in 'ollama list'
    model_id = "llama3.1:8b"
    api_endpoint = "http://localhost:11434/api/generate"



    # Ollama API has a different request structure
    response = requests.post(
        api_endpoint,
        json={
            "model": model_id,
            "prompt": formatted_conversation,
            "stream": False, #To change in another itteration
            "options": {
                "num_predict": 512 
            }
        }
    )
    
    result = response.json()
    # The full response is in the "response" field
    answer = result["response"]
    return answer



memory = []
memory.append({"system" : system_message})


while chatting:
    question = input("You:\n")
    
    # Check for exit command
    if question.lower() == "bye":
        print("\nAI:\nAdiós, amigo! Come back when you're hungry for more conversation! 🌮\n")
        chatting = False
        break
        
    memory.append({"user": question})
    response = simple_agent(memory)
    memory.append({"agent": response})

    print("\nAI:\n" + response + "\n")