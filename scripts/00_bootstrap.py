# 00_bootstrap.py - Bootstrap the assistant
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def create_assistant_with_file(pdf_path):
    """Create assistant and attach file in one step"""
    
    # Upload the file first
    with open(pdf_path, "rb") as file:
        uploaded_file = client.files.create(
            file=file,
            purpose="assistants"
        )
    
    print(f"Uploaded file: {uploaded_file.id}")
    
    # Create assistant with file attached from the start
    try:
        # Try creating with tool_resources (newer API)
        assistant = client.beta.assistants.create(
            name="Study Q&A Assistant",
            instructions=(
                "You are a helpful tutor. "
                "Use the knowledge in the attached files to answer questions. "
                "Cite sources where possible."
            ),
            model="gpt-4o-mini",
            tools=[{"type": "file_search"}],
            tool_resources={"file_search": {"vector_store_files": [uploaded_file.id]}}
        )
        print(f"Created assistant with file attached: {assistant.id}")
        return assistant, uploaded_file.id
        
    except Exception as e:
        print(f"Tool resources approach failed: {e}")
        
        # Try creating with file_ids (legacy API)
        try:
            assistant = client.beta.assistants.create(
                name="Study Q&A Assistant",
                instructions=(
                    "You are a helpful tutor. "
                    "Use the knowledge in the attached files to answer questions. "
                    "Cite sources where possible."
                ),
                model="gpt-4o-mini",
                tools=[{"type": "file_search"}],
                file_ids=[uploaded_file.id]
            )
            print(f"Created assistant with legacy file_ids: {assistant.id}")
            return assistant, uploaded_file.id
            
        except Exception as e2:
            print(f"Legacy file_ids approach failed: {e2}")
            
            # Create assistant without file attachment
            assistant = client.beta.assistants.create(
                name="Study Q&A Assistant",
                instructions=(
                    "You are a helpful tutor. "
                    "Use the knowledge in the attached files to answer questions. "
                    "Cite sources where possible."
                ),
                model="gpt-4o-mini",
                tools=[{"type": "file_search"}]
            )
            print(f"Created assistant without file attachment: {assistant.id}")
            print(f"File uploaded separately: {uploaded_file.id}")
            return assistant, uploaded_file.id

def create_assistant():
    """Create or reuse an assistant with file_search capability"""
    
    # Check if assistant already exists by searching for it
    assistants = client.beta.assistants.list()
    for assistant in assistants.data:
        if assistant.name == "Study Q&A Assistant":
            print(f"Reusing existing assistant: {assistant.id}")
            return assistant
    
    # Create new assistant if none exists (without file for now)
    assistant = client.beta.assistants.create(
        name="Study Q&A Assistant",
        instructions=(
            "You are a helpful tutor. "
            "Use the knowledge in the attached files to answer questions. "
            "Cite sources where possible."
        ),
        model="gpt-4o-mini",
        tools=[{"type": "file_search"}]
    )
    
    print(f"Created new assistant: {assistant.id}")
    return assistant

def upload_pdf_and_attach(assistant, pdf_path):
    """Upload PDF and attach to assistant"""
    
    # Upload the file
    with open(pdf_path, "rb") as file:
        uploaded_file = client.files.create(
            file=file,
            purpose="assistants"
        )
    
    print(f"Uploaded file: {uploaded_file.id}")
    
    # Try different attachment methods based on API version
    try:
        # Try vector stores first (newest API)
        vector_store = client.beta.vector_stores.create(
            name="Study Materials"
        )
        
        # Add file to vector store
        client.beta.vector_stores.files.create(
            vector_store_id=vector_store.id,
            file_id=uploaded_file.id
        )
        
        # Update assistant with vector store
        assistant = client.beta.assistants.update(
            assistant.id,
            tool_resources={"file_search": {"vector_store_ids": [vector_store.id]}}
        )
        
        print(f"Attached file to assistant via vector store: {vector_store.id}")
        
    except (AttributeError, Exception) as e:
        print(f"Vector stores approach failed: {e}")
        print("Trying legacy file attachment method...")
        
        try:
            # Try legacy file_ids approach
            assistant = client.beta.assistants.update(
                assistant.id,
                file_ids=[uploaded_file.id]
            )
            print(f"Attached file using legacy file_ids method: {uploaded_file.id}")
            
        except Exception as e2:
            print(f"Legacy file_ids failed: {e2}")
            print("File uploaded but not attached to assistant.")
            print("You may need to manually attach the file or check your OpenAI API version.")
            print(f"File ID: {uploaded_file.id}")
    
    return assistant, uploaded_file.id

if __name__ == "__main__":
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)  # Go up one level from scripts/
    data_dir = os.path.join(project_root, "data")
    
    print(f"Looking for PDFs in: {data_dir}")
    
    pdf_path = None
    
    if os.path.exists(data_dir):
        pdf_files = [f for f in os.listdir(data_dir) if f.endswith('.pdf')]
        if pdf_files:
            pdf_path = os.path.join(data_dir, pdf_files[0])
            print(f"Found PDF: {pdf_path}")
        else:
            print(f"No PDF files found in {data_dir}/ directory.")
    else:
        print(f"Creating {data_dir}/ directory...")
        os.makedirs(data_dir, exist_ok=True)
        print(f"Please add a PDF file to the {data_dir}/ directory and run again.")
    
    if pdf_path and os.path.exists(pdf_path):
        # Check if assistant already exists
        assistants = client.beta.assistants.list()
        existing_assistant = None
        for assistant in assistants.data:
            if assistant.name == "Study Q&A Assistant":
                existing_assistant = assistant
                break
        
        if existing_assistant:
            print(f"Reusing existing assistant: {existing_assistant.id}")
            # Just upload the file for manual reference
            with open(pdf_path, "rb") as file:
                uploaded_file = client.files.create(
                    file=file,
                    purpose="assistants"
                )
            print(f"Uploaded new file: {uploaded_file.id}")
            print(f"Setup complete! Assistant ID: {existing_assistant.id}")
            print(f"File ID for reference: {uploaded_file.id}")
        else:
            # Create new assistant with file
            assistant, file_id = create_assistant_with_file(pdf_path)
            print(f"Setup complete! Assistant ID: {assistant.id}")
            print(f"File ID: {file_id}")
    else:
        # Create assistant without file
        assistant = create_assistant()
        print("No PDF file available. Please add a PDF to the data/ directory.")
        print("You can use any PDF file for testing - it doesn't have to be calculus_basics.pdf")
