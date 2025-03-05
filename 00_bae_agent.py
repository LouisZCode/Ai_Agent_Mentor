# Import what we need
import requests

# This is our simple agent
def simple_agent(question):
    # Your Hugging Face API token - you'll need to get this from your account
    api_token = ""
    
    # The model we want to use
    model_id = "Qwen/Qwen2.5-Coder-32B-Instruct"
    
    # Where to send our request
    api_url = f"https://api-inference.huggingface.co/models/{model_id}"
    
    # Setting up our request 
    headers = {"Authorization": f"Bearer {api_token}"}
    
    # The question we want to ask, formatted for the model
    prompt = f"<|im_start|>user\n{question}<|im_end|>\n<|im_start|>assistant\n"
    
    # Sending our question to the model
    response = requests.post(
        api_url,
        headers=headers,
        json={"inputs": prompt, "parameters": {"max_new_tokens": 256}}
    )
    
    # Getting the answer
    result = response.json()
    
    # The full response contains the prompt too, so we need to get just the answer part
    # This is a simple way to extract it
    answer = result[0]["generated_text"].split("<|im_start|>assistant\n")[1]
    
    return answer

# Let's use our agent!
question = input("Ask a question to the agent:\n")
response = simple_agent(question)
print(response)