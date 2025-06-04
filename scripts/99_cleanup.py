import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def cleanup_assistant():
    """Delete the assistant and associated files"""
    
    # Find and delete assistant
    assistants = client.beta.assistants.list()
    for assistant in assistants.data:
        if assistant.name == "Study Q&A Assistant":
            client.beta.assistants.delete(assistant.id)
            print(f"Deleted assistant: {assistant.id}")
    
    # List and delete uploaded files
    files = client.files.list()
    for file in files.data:
        if file.purpose == "assistants":
            try:
                client.files.delete(file.id)
                print(f"Deleted file: {file.id}")
            except Exception as e:
                print(f"Could not delete file {file.id}: {e}")
    
    # List and delete vector stores (if available)
    try:
        if hasattr(client.beta, 'vector_stores'):
            vector_stores = client.beta.vector_stores.list()
            for store in vector_stores.data:
                client.beta.vector_stores.delete(store.id)
                print(f"Deleted vector store: {store.id}")
        else:
            print("Vector stores not available in this API version")
    except Exception as e:
        print(f"Error cleaning up vector stores: {e}")

if __name__ == "__main__":
    cleanup_assistant()
    print("Cleanup complete!")
