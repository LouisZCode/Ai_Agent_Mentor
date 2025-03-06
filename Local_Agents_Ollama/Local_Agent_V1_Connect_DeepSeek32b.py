#NOTE - As I was having issues with APIs and the Qwen model in HF
#I decided to first be able to have my LLM locally...
#Its cheaper, and also more reliavle than any API..

#NOTE - I dont think I need so much security here, as I have no API and only I can access my 
#LLM as it is installed in my computer... so will get rid of all the os and dotenv...

import requests

def simple_agent(question):

    # Model name should match exactly as shown in 'ollama list'
    model_id = "deepseek-r1:32b"
    api_endpoint = "http://localhost:11434/api/generate"

    # DeepSeek uses a different prompt format than Qwen
    # Most Ollama models use a more standard format
    prompt = f"User: {question}\n\nAssistant:"
    

    # Ollama API has a different request structure
    response = requests.post(
        api_endpoint,
        json={
            "model": model_id,
            "prompt": prompt,
            "stream": False,  # Get complete response rather than streaming
            "options": {
                "num_predict": 256  # Equivalent to max_new_tokens
            }
        }
    )
    
    result = response.json()
    # The full response is in the "response" field
    answer = result["response"]
    return answer



question = input("Ask a question to the agent:\n")
response = simple_agent(question)
print(response)