import requests
import time
import re

# Model configuration
MODEL = "deepseek-r1:32b"
SHOW_THINKING = False

def remove_thinking(text, show_thinking=SHOW_THINKING):
    """Remove thinking tags only if show_thinking is False"""
    if not show_thinking:
        # Remove anything between <think> and </think> tags
        cleaned = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    else:
        # Keep thinking but make it visually distinct
        cleaned = text.replace('<think>', '\n--- THINKING ---\n').replace('</think>', '\n--- END THINKING ---\n')
    # Always trim leading whitespace
    cleaned = cleaned.lstrip()
    return cleaned

def thinking_cycle(memory, new_question):
    """This gets the full conversation history and the new question and makes the LLM think about it"""
    
    # Format the full conversation history first
    formatted_conversation = ""
    for item in memory:
        if "system" in item:
            formatted_conversation += item["system"]
        elif "user" in item:
            formatted_conversation += f"<|im_start|>user\n{item['user']}<|im_end|>\n"
        elif "agent" in item:
            formatted_conversation += f"<|im_start|>assistant\n{item['agent']}<|im_end|>\n"
    
    # Add the new question
    formatted_conversation += f"<|im_start|>user\n{new_question}<|im_end|>\n"
    
    # Add specific thinking instructions
    formatted_conversation += f"<|im_start|>system\nThink deeply about the user's latest question in the context of the entire conversation. Consider all relevant information from previous exchanges.\n<|im_end|>\n"
    formatted_conversation += "<|im_start|>assistant\n"

    model_id = MODEL
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
    
    return thinking

def simple_agent(memory, thinking):
    """It takes the thought plus the question and gives back an answer"""

    formatted_conversation = ""

    for item in memory:
        if "system" in item:
            formatted_conversation += item["system"]
        elif "user" in item:
            formatted_conversation += f"<|im_start|>user\n{item['user']}<|im_end|>\n"
        elif "agent" in item:
            formatted_conversation += f"<|im_start|>assistant\n{item['agent']}<|im_end|>\n"

    # Add the thinking as system context
    formatted_conversation += f"<|im_start|>system\nBelow is your detailed thinking about the user's question. Use this analysis to provide a clear, concise, and helpful answer. Do not mention that you've done this thinking process.\n\n{thinking}\n<|im_end|>\n"
    formatted_conversation += "<|im_start|>assistant\n"

    # Model name should match exactly as shown in 'ollama list'
    model_id = MODEL
    api_endpoint = "http://localhost:11434/api/generate"

    # Get the complete response first (non-streaming)
    response = requests.post(
        api_endpoint,
        json={
            "model": model_id,
            "prompt": formatted_conversation,
            "stream": False,
            "options": {
                "num_predict": 512
            }
        }
    )
    
    # Extract the full response
    result = response.json()
    full_response = result["response"]
    
    # Clean the response by removing thinking tags and leading whitespace
    cleaned_response = remove_thinking(full_response)
    
    print("\nAI:\n", end="", flush=True)

    for char in cleaned_response:
        print(char, end="", flush=True)
        time.sleep(0.03)
    print("\n")
    # Return the cleaned response for storage in memory
    return cleaned_response

# Main system message
system_message = """<|im_start|>system
You are a helpful AI assistant that provides clear, accurate, and thoughtful responses.
<|im_end|>"""

def main():
    memory = []
    memory.append({"system": system_message})
    chatting = True

    while chatting:
        question = input("You:\n")
        
        # Check for exit command
        if question.lower() in ["bye", "exit", "quit"]:
            print("\nAI:\nThanks for the conversation! 🌮\n")
            chatting = False
            break
            
        # First, get the AI's thinking on the question
        thinking = thinking_cycle(memory, question)
        memory.append({"user": question})

        # Now pass both the original memory and the thinking to get the final response
        response = simple_agent(memory, thinking)
        memory.append({"agent": response})

if __name__ == "__main__":
    main()