# 02_generate_notes.py - Part 2: Generate 10 Exam Notes
import os
import json
import time
from openai import OpenAI
from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError
from typing import List, Optional

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Define the Pydantic schema
class Note(BaseModel):
    id: int = Field(..., ge=1, le=10, description="Note ID from 1 to 10")
    heading: str = Field(..., min_length=1, max_length=100, example="Mean Value Theorem")
    summary: str = Field(..., max_length=150, description="Concise summary of the concept")
    page_ref: Optional[int] = Field(None, description="Page number in source PDF")

class NotesResponse(BaseModel):
    notes: List[Note] = Field(..., min_items=10, max_items=10, description="Exactly 10 study notes")

def get_assistant_and_file():
    """Get the existing assistant and file for context"""
    try:
        # Get assistant
        assistants = client.beta.assistants.list()
        assistant = None
        for a in assistants.data:
            if a.name == "Study Q&A Assistant":
                assistant = a
                break
        
        if not assistant:
            print("No assistant found. Please run 00_bootstrap.py first.")
            return None, None
        
        # Get the most recent PDF file
        files = client.files.list()
        latest_file = None
        for file in files.data:
            if file.purpose == "assistants" and file.filename.endswith('.pdf'):
                latest_file = file
                break
        
        return assistant, latest_file
    
    except Exception as e:
        print(f"Error getting assistant/file: {e}")
        return None, None

def generate_notes_with_assistant(assistant_id, file_id=None):
    """Generate notes using the assistant with file context"""
    try:
        # Create a thread
        thread = client.beta.threads.create()
        
        # Prepare the request for 10 study notes
        request_message = (
            "Please analyze the attached study material and create exactly 10 concise study notes. "
            "Each note should have:\n"
            "- A unique ID from 1 to 10\n"
            "- A clear heading (concept name)\n"
            "- A summary under 150 characters\n"
            "- Page reference if available\n\n"
            "Focus on the most important concepts for exam preparation. "
            "Return the response as a JSON object with a 'notes' array containing exactly 10 note objects."
        )
        
        # Prepare message data
        message_data = {
            "thread_id": thread.id,
            "role": "user",
            "content": request_message
        }
        
        # Try to attach file if available
        if file_id:
            try:
                message_data["attachments"] = [
                    {
                        "file_id": file_id,
                        "tools": [{"type": "file_search"}]
                    }
                ]
                print(f"Attaching file {file_id} for content analysis...")
            except Exception:
                try:
                    message_data["file_ids"] = [file_id]
                    print(f"Using legacy file attachment for {file_id}...")
                except Exception:
                    print("Proceeding without file attachment...")
        
        # Create message
        client.beta.threads.messages.create(**message_data)
        
        # Run the assistant
        run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=assistant_id
        )
        
        # Wait for completion
        print("Generating study notes...")
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
                return None
            
            print(".", end="", flush=True)
            time.sleep(1)
            attempts += 1
        
        print("\n")
        
        # Get the response
        messages = client.beta.threads.messages.list(thread_id=thread.id)
        response_content = messages.data[0].content[0].text.value
        
        return response_content
        
    except Exception as e:
        print(f"Error generating notes with assistant: {e}")
        return None

def generate_notes_direct():
    """Generate notes using direct chat completion (fallback method)"""
    
    system_prompt = (
        "You are a study summarizer. "
        "Return exactly 10 unique notes that will help prepare for the exam. "
        "Each note must have: id (1-10), heading, summary (max 150 chars), and optional page_ref. "
        "Respond *only* with valid JSON matching this schema: "
        "{'notes': [{'id': int, 'heading': str, 'summary': str, 'page_ref': int|null}, ...]} "
        "Focus on key mathematical concepts like calculus, derivatives, integrals, theorems, and formulas."
    )
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": system_prompt}],
            response_format={"type": "json_object"},
            temperature=0.7
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        print(f"Error with direct generation: {e}")
        return None

def validate_and_create_notes(json_content):
    """Validate JSON content and create Note objects"""
    try:
        # Parse JSON
        data = json.loads(json_content)
        
        # Validate structure
        notes_response = NotesResponse(**data)
        
        return notes_response.notes
        
    except json.JSONDecodeError as e:
        print(f"Invalid JSON: {e}")
        return None
    except ValidationError as e:
        print(f"Validation error: {e}")
        return None
    except Exception as e:
        print(f"Error creating notes: {e}")
        return None

def print_pretty_notes(notes):
    """Print notes in a beautifully formatted way"""
    print("\n" + "="*65)
    print("           📚 STUDY NOTES FOR EXAM PREPARATION 📚")
    print("="*65)
    
    for note in notes:
        print(f"\n📝 NOTE {note.id}: {note.heading}")
        print("─" * 50)
        print(f"💡 Summary: {note.summary}")
        if note.page_ref:
            print(f"📄 Page Reference: {note.page_ref}")
        else:
            print("📄 Page Reference: Not specified")
        print("─" * 50)

def save_notes_to_file(notes, filename="exam_notes.json"):
    """Save notes to JSON file with pretty formatting"""
    try:
        # Convert notes to dictionaries
        notes_data = {
            "exam_notes": [note.model_dump() for note in notes],
            "metadata": {
                "total_notes": len(notes),
                "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "purpose": "Exam preparation study notes"
            }
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(notes_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Notes successfully saved to '{filename}'")
        print(f"📁 File location: {os.path.abspath(filename)}")
        print(f"📊 Total notes saved: {len(notes)}")
        
    except Exception as e:
        print(f"❌ Error saving notes: {e}")

def print_notes_summary(notes):
    """Print a quick summary of the generated notes"""
    print(f"\n📋 NOTES SUMMARY:")
    print(f"   • Total notes generated: {len(notes)}")
    print(f"   • Notes with page references: {sum(1 for note in notes if note.page_ref)}")
    print(f"   • Average summary length: {sum(len(note.summary) for note in notes) // len(notes)} characters")
    
    print(f"\n📚 Quick overview:")
    for note in notes:
        page_info = f" (p.{note.page_ref})" if note.page_ref else ""
        print(f"   {note.id}. {note.heading}{page_info}")

def save_notes_as_markdown(notes, filename="exam_notes.md"):
    """Save notes as a markdown file for easy reading"""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("# 📚 Study Notes for Exam Preparation\n\n")
            f.write(f"*Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}*\n\n")
            f.write("---\n\n")
            
            for note in notes:
                f.write(f"## {note.id}. {note.heading}\n\n")
                f.write(f"**Summary:** {note.summary}\n\n")
                if note.page_ref:
                    f.write(f"**Page Reference:** {note.page_ref}\n\n")
                f.write("---\n\n")
        
        print(f"📝 Notes also saved as Markdown: '{filename}'")
        
    except Exception as e:
        print(f"❌ Error saving markdown: {e}")

def main():
    """Main function to generate study notes"""
    print("🚀 Starting Study Notes Generation...")
    
    # Method 1: Try using assistant with file context
    assistant, file = get_assistant_and_file()
    
    json_content = None
    
    if assistant:
        print(f"Using assistant: {assistant.id}")
        if file:
            print(f"Using file: {file.filename} (ID: {file.id})")
        
        json_content = generate_notes_with_assistant(
            assistant.id, 
            file.id if file else None
        )
    
    # Method 2: Fallback to direct generation if assistant method fails
    if not json_content:
        print("Trying direct generation method...")
        json_content = generate_notes_direct()
    
    if not json_content:
        print("❌ Failed to generate notes")
        return
    
    # Validate and create notes
    notes = validate_and_create_notes(json_content)
    
    if not notes:
        print("❌ Failed to validate notes")
        print("Raw JSON content:")
        print(json_content)
        return
    
    # Display results
    print_notes_summary(notes)
    print_pretty_notes(notes)
    
    # Save to both JSON and Markdown
    save_notes_to_file(notes)
    save_notes_as_markdown(notes)
    
    print("\n🎉 Study notes generation complete!")
    print(f"📊 Generated {len(notes)} notes successfully.")
    print("\n📁 Files created:")
    print("   • exam_notes.json (structured data)")
    print("   • exam_notes.md (readable format)")

if __name__ == "__main__":
    main()