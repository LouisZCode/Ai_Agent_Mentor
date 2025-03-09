import requests
import re

class ChatbotModel:
    """
    Model class that handles the AI logic and conversation memory
    """
    def __init__(self, model_name="llama3.1:8b"):
        self.model_name = model_name
        self.api_endpoint = "http://localhost:11434/api/generate"
        
        # Initialize conversation memory
        self.system_message = """<|im_start|>system
You are a helpful AI assistant that provides clear, accurate, and thoughtful responses.
<|im_end|>"""
        self.memory = [{"system": self.system_message}]
    
    def reset_memory(self):
        """Reset memory to initial state"""
        self.memory = [{"system": self.system_message}]
    
    def add_to_memory(self, role, content):
        """Add a message to the conversation memory"""
        self.memory.append({role: content})
    
    def remove_thinking(self, text, show_thinking=False):
        """Remove thinking tags based on show_thinking setting"""
        if not show_thinking:
            # Remove anything between <think> and </think> tags
            cleaned = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
        else:
            # Keep thinking but make it visually distinct
            cleaned = text.replace('<think>', '\n--- THINKING ---\n').replace('</think>', '\n--- END THINKING ---\n')
        # Always trim leading whitespace
        cleaned = cleaned.lstrip()
        return cleaned
    
    def format_conversation(self):
        """Format the conversation history for the AI model"""
        formatted_conversation = ""
        for item in self.memory:
            if "system" in item:
                formatted_conversation += item["system"]
            elif "user" in item:
                formatted_conversation += f"<|im_start|>user\n{item['user']}<|im_end|>\n"
            elif "agent" in item:
                formatted_conversation += f"<|im_start|>assistant\n{item['agent']}<|im_end|>\n"
        return formatted_conversation
    
    def generate_thinking(self, question):
        """Generate the AI's thinking about a question"""
        # Format the conversation history
        formatted_conversation = self.format_conversation()
        
        # Add the new question
        formatted_conversation += f"<|im_start|>user\n{question}<|im_end|>\n"
        
        # Add specific thinking instructions
        formatted_conversation += f"<|im_start|>system\nThink deeply about the user's latest question in the context of the entire conversation. Consider all relevant information from previous exchanges.\n<|im_end|>\n"
        formatted_conversation += "<|im_start|>assistant\n"
        
        try:
            # Make API request
            response = requests.post(
                self.api_endpoint,
                json={
                    "model": self.model_name,
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
        except Exception as e:
            return f"Error in thinking cycle: {str(e)}"
    
    def generate_response(self, thinking, show_thinking):
        """Generate the AI's response based on the thinking"""
        # Format the conversation with thinking as context
        formatted_conversation = self.format_conversation()
        
        # Add the thinking as system context
        formatted_conversation += f"<|im_start|>system\nBelow is your detailed thinking about the user's question. Use this analysis to provide a clear, concise, and helpful answer. Do not mention that you've done this thinking process.\n\n{thinking}\n<|im_end|>\n"
        formatted_conversation += "<|im_start|>assistant\n"
        
        try:
            # Make API request
            response = requests.post(
                self.api_endpoint,
                json={
                    "model": self.model_name,
                    "prompt": formatted_conversation,
                    "stream": False,
                    "options": {
                        "num_predict": 512
                    }
                }
            )
            
            # Extract and clean the response
            result = response.json()
            full_response = result["response"]
            cleaned_response = self.remove_thinking(full_response, show_thinking)
            
            return cleaned_response
        except Exception as e:
            return f"Error: {str(e)}"