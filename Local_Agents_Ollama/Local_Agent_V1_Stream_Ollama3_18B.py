#NOTE - I wanted to add a while loop to continue the conversation with my local DeepSeek model.
#Also, I want for now to take away the thniking part, so I can focus on the result sof the
#conversation. We can add the thinking part later

#NOTE - Maybe also good idea to have anothe rModel just in case?


chatting = True
import json
import requests
import time  # Add this import

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



    # Change the streaming parameter to True
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
        stream=True  # Enable streaming at the requests level
    )
    
    # Initialize an empty string to build the complete response
    full_response = ""
    
    # Print a newline before starting to stream output
    print("\nAI:", end="", flush=True)
    
    # Process each chunk as it arrives
    for line in response.iter_lines():
        if line:
            # Parse the JSON chunk
            chunk = json.loads(line)
            
            # Extract the text from the chunk
            chunk_text = chunk.get("response", "")
            
            # Check if this is the end of the sequence
            if chunk.get("done", False):
                break

            # Add a small delay between chunks (adjust the value to control speed)
            time.sleep(0.03)  # 30ms delay - adjust this value to your preference
                
            # Print the chunk without a newline to create a continuous stream effect
            print(chunk_text, end="", flush=True)
            
            # Add to our complete response
            full_response += chunk_text
    
    # Print a newline after we're done
    print("\n")
    
    # Return the complete response for memory storage
    return full_response



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
