import tkinter as tk
from model import ChatbotModel
from view import ChatbotView
from controller import ChatbotController

def main():
    """Main entry point for the chatbot application"""
    # Create the root Tkinter window
    root = tk.Tk()
    
    # Create the MVC components
    model = ChatbotModel()  # We'll set the model name from the view's selection
    view = ChatbotView(root)
    controller = ChatbotController(model, view)
    
    # Start the Tkinter event loop
    root.mainloop()

if __name__ == "__main__":
    main() 