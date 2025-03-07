#NOTE  this 2 stage reasoning would make the LLM think about the question
#and then send that thinking and the original question to the LLM again.
#The fisrt part is not visible, the second one of course it is (its the final answer)



chatting = True
import json
import requests
import time  # Add this import




system_message = """<|im_start|>system
You are a helpful AI assistant that thinks carefully before answering questions.

When responding to complex questions, always follow these steps:
1. Understand the question fully. Identify the key parts that need to be addressed.
2. Think about what knowledge or information is relevant to answering this question.
3. Consider different approaches or perspectives on the question.
4. Reason step-by-step through the problem.
5. Provide a clear, concise answer based on your reasoning.

Your thinking process should be thorough but invisible to the user - they should only see your final, polished answer.
You tell the user that you carefully tought about the question if you did
<|im_end|>"""

#NOTE I wil create a function that will only make the LLM think more about the answer
#After that, I can pass the original question AND the thinking to the LLM again
#So it has more context

def thinking_stage(memory):
    pass



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
    print("\nAI:\n", end="", flush=True)
    
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
