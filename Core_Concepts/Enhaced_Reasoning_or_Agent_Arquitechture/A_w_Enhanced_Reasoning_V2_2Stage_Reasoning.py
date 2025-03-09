#NOTE  this 2 stage reasoning would make the LLM think about the question
#and then send that thinking and the original question to the LLM again.
#The fisrt part is not visible, the second one of course it is (its the final answer)


#NOTE - Interestingly, the thinking happens only oonce per message sent, aka, the AI
# does not remember the previous thinking and goes out of context... we cna fix this
# by making the thinking also go trought the memory, making it last more there


chatting = True
import json
import requests
import time  # Add this import

#system_message = tbd

#NOTE I wil create a function that will only make the LLM think more about the answer
#After that, I can pass the original question AND the thinking to the LLM again
#So it has more context

def thinking_cycle(question):
    """This one gets the question from the user and makes the LLM think about it"""
    
    formatted_conversation = f"<|im_start|>system\nYou are an AI assistant. Think deeply about this question. Explore multiple perspectives and analyze all aspects thoroughly. This is just your internal thinking process.\n<|im_end|>\n<|im_start|>user\n{question}<|im_end|>\n<|im_start|>assistant\n"


    model_id = "llama3.1:8b"
    api_endpoint = "http://localhost:11434/api/generate"


    response = requests.post(
        api_endpoint,
        json={
            "model": model_id,
            "prompt": formatted_conversation,
            "stream": False,
            "options": {
                "num_predict": 512 
            }
        },
    )
        
    # Extract the thinking from the response
    result = response.json()
    thinking = result["response"]

    # For debugging (remove in production)
    print("Thinking process:\n", thinking)

    return thinking



def simple_agent(memory, thinking):
    """It takes the tought plus the question and gives back an answer"""

    formatted_conversation = ""

    for item in memory:
        if "system" in item:
            formatted_conversation += item["system"]  # Use value from dictionary
        elif "user" in item:
            formatted_conversation += f"<|im_start|>user\n{item['user']}<|im_end|>\n"
        elif "agent" in item:
            formatted_conversation += f"<|im_start|>assistant\n{item['agent']}<|im_end|>\n"

    formatted_conversation += f"<|im_start|>system\nBelow is your detailed thinking about the user's question. Use this analysis to provide a clear, concise, and helpful answer. Do not mention that you've done this thinking process.\n\n{thinking}\n<|im_end|>\n"

    formatted_conversation += "<|im_start|>assistant\n"


    # Model name should match exactly as shown in 'ollama list'
    model_id = "llama3.1:8b"
    api_endpoint = "http://localhost:11434/api/generate"


    response = requests.post(
        api_endpoint,
        json={
            "model": model_id,
            "prompt": formatted_conversation,
            "stream": True,
            "options": {
                "num_predict": 512 
            }
        },
        stream=True  
    )
    
    full_response = ""
    
    print("\nAI:\n", end="", flush=True)
    
    for line in response.iter_lines():
        if line:
            chunk = json.loads(line)
            
            chunk_text = chunk.get("response", "")
            
            if chunk.get("done", False):
                break

            time.sleep(0.03) 
                
            print(chunk_text, end="", flush=True)
            
            full_response += chunk_text
    
    print("\n")
    return full_response



memory = []
#memory.append({"system" : system_message})


while chatting:

    question = input("You:\n")
    
    # Check for exit command
    if question.lower() == "bye":
        print("\nAI:\nThanks for the conversation! 🌮\n")
        chatting = False
        break
        
    # First, get the AI's thinking on the question
    thinking = thinking_cycle(question)

    memory.append({"user": question})

    # Now pass both the original memory and the thinking to get the final response
    # We need to modify your simple_agent function to accept thinking as an additional parameter
    response = simple_agent(memory, thinking)

    # Store the response in memory
    memory.append({"agent": response})
