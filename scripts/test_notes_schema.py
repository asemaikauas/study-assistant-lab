# test_notes_schema.py - Optional pytest validation
import pytest
from pydantic import ValidationError
from notes_schema import Note, NotesResponse

def test_valid_note():
    """Test creating a valid note"""
    note = Note(
        id=1,
        heading="Summary of the book",
        summary="States that",
        page_ref=42
    )
    
    assert note.id == 1
    assert note.heading == "Mean Value Theorem"
    assert len(note.summary) <= 150
    assert note.page_ref == 42

def test_note_validation_errors():
    """Test note validation errors"""
    
    # Invalid ID (out of range)
    with pytest.raises(ValidationError):
        Note(id=11, heading="Test", summary="Test summary")
    
    # Invalid ID (zero)
    with pytest.raises(ValidationError):
        Note(id=0, heading="Test", summary="Test summary")
    
    # Empty heading
    with pytest.raises(ValidationError):
        Note(id=1, heading="", summary="Test summary")
    
    # Summary too long
    with pytest.raises(ValidationError):
        Note(id=1, heading="Test", summary="x" * 151)

def test_note_optional_page_ref():
    """Test note with optional page reference"""
    
    # With page reference
    note_with_page = Note(
        id=1,
        heading="Test Concept",
        summary="Test summary",
        page_ref=10
    )
    assert note_with_page.page_ref == 10
    
    # Without page reference
    note_without_page = Note(
        id=2,
        heading="Another Concept",
        summary="Another summary"
    )
    assert note_without_page.page_ref is None

def test_notes_response():
    """Test NotesResponse with exactly 10 notes"""
    
    notes_data = []
    for i in range(1, 11):
        notes_data.append({
            "id": i,
            "heading": f"Concept {i}",
            "summary": f"Summary for concept {i}",
            "page_ref": i * 10
        })
    
    response = NotesResponse(notes=notes_data)
    assert len(response.notes) == 10
    
    # Check that all notes are properly created
    for i, note in enumerate(response.notes):
        assert note.id == i + 1
        assert note.heading == f"Concept {i + 1}"

def test_notes_response_wrong_count():
    """Test NotesResponse with wrong number of notes"""
    
    # Too few notes
    with pytest.raises(ValidationError):
        NotesResponse(notes=[
            {"id": 1, "heading": "Test", "summary": "Test"}
        ])
    
    # Too many notes
    notes_data = []
    for i in range(1, 12):  # 11 notes
        notes_data.append({
            "id": i,
            "heading": f"Concept {i}",
            "summary": f"Summary for concept {i}"
        })
    
    with pytest.raises(ValidationError):
        NotesResponse(notes=notes_data)

def test_notes_response_empty():
    """Test NotesResponse with empty notes list"""
    
    with pytest.raises(ValidationError):
        NotesResponse(notes=[])

def test_note_heading_length():
    """Test note heading length constraints"""
    
    # Valid heading
    note = Note(
        id=1,
        heading="A" * 50,  # 50 characters should be fine
        summary="Test summary"
    )
    assert len(note.heading) == 50
    
    # Heading too long
    with pytest.raises(ValidationError):
        Note(
            id=1,
            heading="A" * 101,  # 101 characters should fail
            summary="Test summary"
        )

if __name__ == "__main__":
    pytest.main([__file__, "-v"])