import os
import time
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def get_assistant():
    """Get the existing assistant"""
    assistants = client.beta.assistants.list()
    for assistant in assistants.data:
        if assistant.name == "Study Q&A Assistant":
            return assistant
    raise ValueError("Assistant not found. Please run 00_bootstrap.py first.")

def get_file_name(file_id):
    """Get the actual filename from file ID"""
    try:
        file_info = client.files.retrieve(file_id)
        return file_info.filename
    except Exception as e:
        print(f"Could not retrieve filename for {file_id}: {e}")
        return f"Unknown file ({file_id})"

def ask_question(assistant_id, question, file_id=None):
    """Ask a question to the assistant and get response with citations"""
    
    try:
        # Create a thread
        thread = client.beta.threads.create()
        
        # Prepare message content
        message_data = {
            "thread_id": thread.id,
            "role": "user",
            "content": question
        }
        
        # Try to attach file to the message if file_id is provided
        if file_id:
            try:
                # Try new attachments format first
                message_data["attachments"] = [
                    {
                        "file_id": file_id,
                        "tools": [{"type": "file_search"}]
                    }
                ]
                print(f"Attaching file {file_id} to message...")
            except Exception as e:
                try:
                    # Try legacy file_ids format
                    message_data["file_ids"] = [file_id]
                    print(f"Using legacy file attachment for {file_id}...")
                except Exception as e2:
                    print(f"Could not attach file: {e2}")
        
        # Add message to thread
        message = client.beta.threads.messages.create(**message_data)
        
        # Run the assistant
        run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=assistant_id
        )
        
        # Wait for completion
        print("Processing your question...")
        max_attempts = 30
        attempts = 0
        
        while attempts < max_attempts:
            run = client.beta.threads.runs.retrieve(
                thread_id=thread.id,
                run_id=run.id
            )
            
            if run.status == "completed":
                break
            elif run.status == "failed":
                print(f"Run failed: {run.last_error}")
                return None, None
            elif run.status in ["cancelled", "expired"]:
                print(f"Run {run.status}")
                return None, None
            
            print(".", end="", flush=True)
            time.sleep(1)
            attempts += 1
        
        if attempts >= max_attempts:
            print("\nTimeout waiting for response")
            return None, None
        
        print("\n")
        
        # Get the response
        messages = client.beta.threads.messages.list(thread_id=thread.id)
        response_message = messages.data[0]
        
        # Extract answer
        if response_message.content and len(response_message.content) > 0:
            answer = response_message.content[0].text.value
        else:
            answer = "No response received"
        
        citations = []
        
        # Extract file citations if present
        if hasattr(response_message.content[0].text, 'annotations'):
            for annotation in response_message.content[0].text.annotations:
                if hasattr(annotation, 'file_citation'):
                    file_citation = annotation.file_citation
                    file_name = get_file_name(file_citation.file_id)
                    citations.append({
                        'file_id': file_citation.file_id,
                        'citation': file_name
                    })
                elif hasattr(annotation, 'file_path'):
                    # Handle file_path annotations differently
                    file_id = getattr(annotation.file_path, 'file_id', 'Unknown')
                    file_name = get_file_name(file_id) if file_id != 'Unknown' else 'Unknown file'
                    citations.append({
                        'file_id': file_id,
                        'citation': file_name
                    })
        
        return answer, citations
        
    except Exception as e:
        print(f"Error in ask_question: {e}")
        return None, None

def main():
    """Main function to run the Q&A assistant"""
    
    try:
        assistant = get_assistant()
        print(f"Using assistant: {assistant.id}")
        
        # Try to get the most recent file ID
        files = client.files.list()
        latest_file_id = None
        for file in files.data:
            if file.purpose == "assistants" and file.filename.endswith('.pdf'):
                latest_file_id = file.id
                print(f"Found file: {file.filename} (ID: {file.id})")
                break
        
        if not latest_file_id:
            print("No PDF files found. The assistant will work with general knowledge only.")
        
        print("=" * 50)
        
        # Test questions
        test_questions = [
            "provide a summary of the book"
        ]
        
        for question in test_questions:
            print(f"\nQuestion: {question}")
            print("-" * 30)
            
            answer, citations = ask_question(assistant.id, question, latest_file_id)
            
            if answer:
                print(f"Answer: {answer}")
                
                if citations:
                    print("\nCitations:")
                    for i, citation in enumerate(citations, 1):
                        print(f"{i}. Source: {citation['citation']}")
                        print(f"   File ID: {citation['file_id']}")
                else:
                    print("\nNo citations found - answer may be from general knowledge.")
            
            print("=" * 50)
        
        # Interactive mode
        print("\nEntering interactive mode. Type 'quit' to exit.")
        while True:
            question = input("\nYour question: ").strip()
            
            if question.lower() in ['quit', 'exit', 'q']:
                break
            
            if question:
                answer, citations = ask_question(assistant.id, question, latest_file_id)
                
                if answer:
                    print(f"\nAnswer: {answer}")
                    
                    if citations:
                        print("\nCitations:")
                        for i, citation in enumerate(citations, 1):
                            print(f"{i}. Source: {citation['citation']}")
                            print(f"   File ID: {citation['file_id']}")
                    else:
                        print("\nNo citations found - answer may be from general knowledge.")
    
    except Exception as e:
        print(f"Error: {e}")
        print("Make sure to run 00_bootstrap.py first to create the assistant.")

if __name__ == "__main__":
    main()
