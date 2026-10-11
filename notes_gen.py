import requests
import json
import re
import os
from typing import List, Dict, Any
import textwrap
from fpdf import FPDF
import unicodedata

def clean_text_for_pdf(text: str) -> str:
    """
    Clean text to remove problematic Unicode characters for PDF generation.
    
    Args:
        text: Input text that may contain Unicode characters
        
    Returns:
        Cleaned text safe for PDF generation
    """
    if not text:
        return ""
    
    # Replace common problematic Unicode characters
    replacements = {
        '\u2019': "'",  # Right single quotation mark
        '\u2018': "'",  # Left single quotation mark
        '\u201c': '"',  # Left double quotation mark
        '\u201d': '"',  # Right double quotation mark
        '\u2013': '-',  # En dash
        '\u2014': '--', # Em dash
        '\u2026': '...', # Horizontal ellipsis
        '\u00a0': ' ',  # Non-breaking space
        '\u2022': '•',  # Bullet point
    }
    
    for unicode_char, replacement in replacements.items():
        text = text.replace(unicode_char, replacement)
    
    # Normalize Unicode characters to their closest ASCII equivalents
    try:
        text = unicodedata.normalize('NFKD', text)
        text = text.encode('ascii', 'ignore').decode('ascii')
    except:
        # If normalization fails, remove non-ASCII characters
        text = ''.join(char for char in text if ord(char) < 128)
    
    return text

def clean_markdown(text: str) -> str:
    """
    Remove markdown formatting characters from text.
    
    Args:
        text: Text containing markdown formatting
        
    Returns:
        Cleaned text without markdown formatting
    """
    # Remove bold/italic markers
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)  # Bold
    text = re.sub(r'\*(.*?)\*', r'\1', text)      # Italic

    # Remove backticks for code
    text = re.sub(r'`(.*?)`', r'\1', text)

    # Remove other common markdown formatters
    text = re.sub(r'__(.*?)__', r'\1', text)      # Underline/bold
    text = re.sub(r'~~(.*?)~~', r'\1', text)      # Strikethrough

    return text.strip()

def chunk_text(text: str, chunk_size: int = 3000) -> List[str]:
    """
    Split text into manageable chunks for processing.
    
    Args:
        text: The input text to chunk
        chunk_size: Maximum size of each chunk in characters

    Returns:
        List of text chunks
    """
    # Use textwrap to split text into paragraphs first
    paragraphs = text.split('\n\n')
    chunks = []
    current_chunk = ""

    for paragraph in paragraphs:
        # If adding this paragraph would exceed chunk size, save current chunk and start new one
        if len(current_chunk) + len(paragraph) > chunk_size and current_chunk:
            chunks.append(current_chunk.strip())
            current_chunk = paragraph
        else:
            if current_chunk:
                current_chunk += "\n\n" + paragraph
            else:
                current_chunk = paragraph

    # Add the last chunk if it's not empty
    if current_chunk:
        chunks.append(current_chunk.strip())
        
    return chunks

def extract_title(content: str) -> str:
    """
    Extract a concise title from provided content using Qwen.
    
    Args:
        content: Text content to extract title from
        
    Returns:
        A concise title for the content
    """
    prompt = f"""Extract a concise, descriptive title (2-5 words) from the following content.

Return only the title without any extra text or explanation.

Content: {content[:1000]}"""  # Using first 1000 chars for title extraction

    try:
        response = requests.post(
            'http://localhost:11434/api/generate',
            json={
                "model": "qwen2.5:latest",
                "prompt": prompt,
                "stream": False
            }
        )
        title = response.json()['response'].strip()
        # Clean title for safe usage
        return clean_text_for_pdf(title)
    except Exception as e:
        print(f"Error extracting title: {e}")
        return "Untitled Notes"

def generate_notes_for_chunk(chunk: str, title: str) -> Dict[str, Any]:
    """
    Generate detailed notes for a text chunk using Qwen.
    
    Args:
        chunk: Text chunk to process
        title: Overall document title
        
    Returns:
        Dictionary containing structured notes
    """
    prompt = f"""Create detailed academic notes for the content below about "{title}".

Format your response with these sections:

1. MAIN NOTES: Write comprehensive notes in a flowing text format with clear headings and subheadings. Structure it like a well-organized study guide with topics, subtopics, and detailed explanations. Use natural paragraph formatting.

2. KEY TERMS: Extract important vocabulary/terminology with precise definitions

3. EXAMPLES: Include 2-3 relevant examples or applications

4. CONNECTIONS: Note relationships to other concepts or topics

5. QUESTIONS: Create 2-3 study questions that test understanding

Format exactly as shown:

MAIN NOTES:

[Write comprehensive notes in flowing paragraph format with clear topic headings and detailed explanations]

KEY TERMS:
• [Term 1]: [Definition]
• [Term 2]: [Definition]

EXAMPLES:

1. [Example 1]
2. [Example 2]

CONNECTIONS:

* [Connection 1]
* [Connection 2]

QUESTIONS:

1. [Question 1]
2. [Question 2]

Content to analyze:
{chunk}
"""

    try:
        response = requests.post(
            'http://localhost:11434/api/generate',
            json={
                "model": "qwen2.5:latest",
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.3}
            }
        )
        
        notes_text = response.json()['response']
        
        # Clean markdown formatting from the response
        notes_text = clean_markdown(notes_text)
        
        # Clean Unicode characters for PDF compatibility
        notes_text = clean_text_for_pdf(notes_text)
        
        # Parse the formatted response into a dictionary
        notes = {}
        
        # Extract main notes as a single text block
        main_notes_match = re.search(r'MAIN NOTES:(.*?)(?=KEY TERMS:|$)', notes_text, re.DOTALL)
        if main_notes_match:
            main_notes_text = main_notes_match.group(1).strip()
            notes["main_notes"] = main_notes_text
        else:
            notes["main_notes"] = ""
        
        # Extract key terms
        key_terms_match = re.search(r'KEY TERMS:(.*?)(?=EXAMPLES:|$)', notes_text, re.DOTALL)
        key_terms = {}
        if key_terms_match:
            key_terms_text = key_terms_match.group(1).strip()
            
            for line in key_terms_text.split('\n'):
                line = line.strip()
                if line.startswith('• ') or line.startswith('* '):
                    parts = line[2:].split(':', 1)
                    if len(parts) == 2:
                        term, definition = parts
                        key_terms[term.strip()] = definition.strip()
                        
        notes["key_terms"] = key_terms
        
        # Extract examples
        examples_match = re.search(r'EXAMPLES:(.*?)(?=CONNECTIONS:|$)', notes_text, re.DOTALL)
        examples = []
        if examples_match:
            examples_text = examples_match.group(1).strip()
            
            for line in examples_text.split('\n'):
                line = line.strip()
                if re.match(r'^\d+\.', line):
                    examples.append(line[line.find('.')+1:].strip())
                    
        notes["examples"] = examples
        
        # Extract connections
        connections_match = re.search(r'CONNECTIONS:(.*?)(?=QUESTIONS:|$)', notes_text, re.DOTALL)
        connections = []
        if connections_match:
            connections_text = connections_match.group(1).strip()
            
            for line in connections_text.split('\n'):
                line = line.strip()
                if line.startswith('* ') or line.startswith('- '):
                    connections.append(line[2:].strip())
                    
        notes["connections"] = connections
        
        # Extract questions
        questions_match = re.search(r'QUESTIONS:(.*?)(?=$)', notes_text, re.DOTALL)
        questions = []
        if questions_match:
            questions_text = questions_match.group(1).strip()
            
            for line in questions_text.split('\n'):
                line = line.strip()
                if re.match(r'^\d+\.', line):
                    questions.append(line[line.find('.')+1:].strip())
                    
        notes["questions"] = questions
                
        return notes
        
    except Exception as e:
        print(f"Error generating notes: {e}")
        return {
            "main_notes": "Error processing this chunk",
            "key_terms": {},
            "examples": [],
            "connections": [],
            "questions": []
        }

def create_notes(text: str, chunk_size: int = 3000) -> Dict[str, Any]:
    """
    Process text input and generate comprehensive Cornell-style notes.
    For long texts, chunks the content and processes each chunk separately.
    
    Args:
        text: Input text to process
        chunk_size: Maximum size of chunks for processing
        
    Returns:
        Dictionary containing the generated notes
    """
    # Extract overall title from the beginning of the text
    title = extract_title(text)

    # Chunk the text if it's long
    chunks = chunk_text(text, chunk_size)
    print(f"Processing {len(chunks)} chunks for document: {title}")

    # Generate notes for each chunk
    all_notes = []
    for i, chunk in enumerate(chunks):
        print(f"Processing chunk {i+1}/{len(chunks)}...")
        chunk_notes = generate_notes_for_chunk(chunk, title)
        all_notes.append(chunk_notes)

    # Combine notes into a unified structure
    combined_notes = {
        "title": title,
        "chunk_count": len(chunks),
        "main_notes": "",  # Now a single string instead of list
        "key_terms": {},
        "examples": [],
        "connections": [],
        "questions": []
    }

    # Combine main notes into a single text block
    main_notes_sections = []
    for notes in all_notes:
        main_text = notes.get("main_notes", "").strip()
        if main_text:
            main_notes_sections.append(main_text)
    
    # Join all main notes sections with double newlines
    combined_notes["main_notes"] = "\n\n".join(main_notes_sections)

    # Combine other sections
    for notes in all_notes:
        # Combine key terms
        combined_notes["key_terms"].update(notes.get("key_terms", {}))
        
        # Append examples, connections, and questions
        combined_notes["examples"].extend(notes.get("examples", []))
        combined_notes["connections"].extend(notes.get("connections", []))
        combined_notes["questions"].extend(notes.get("questions", []))

    print(f"✅ Generated comprehensive notes for: {title}")
    return combined_notes

def export_notes_to_pdf(notes: Dict[str, Any], output_file: str = None) -> str:
    """
    Export notes data to a well-formatted PDF with proper text wrapping
    and minimal styling.
    """
    title = notes.get("title", "Untitled Notes")
    # Clean title for PDF generation
    title = clean_text_for_pdf(title)
    
    if not output_file:
        clean_title = re.sub(r'[\\/*?:"<>|]', "", title)
        clean_title = clean_title.replace(' ', '_')
        output_dir = r"D:\Downloads\Edumate\static\notes"
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, f"{clean_title}_notes.pdf")

    class PDF(FPDF):
        def header(self):
            self.set_font('helvetica', 'B', 14)
            # Clean title text for PDF
            clean_title = clean_text_for_pdf(title)
            self.cell(0, 10, clean_title, 0, 1, 'C')
            self.ln(5)
            
        def footer(self):
            self.set_y(-15)
            self.set_font('helvetica', 'I', 8)
            self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

    try:
        pdf = PDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        pdf.set_left_margin(20)
        pdf.set_right_margin(20)

        # Main Notes Section - now as continuous text
        pdf.set_font('helvetica', 'B', 12)
        pdf.cell(0, 8, "MAIN NOTES", 0, 1)
        pdf.ln(5)
        
        pdf.set_font('helvetica', '', 11)
        main_notes_text = notes.get("main_notes", "")
        if main_notes_text:
            # Clean the main notes text for PDF
            main_notes_text = clean_text_for_pdf(main_notes_text)
            pdf.multi_cell(0, 6, main_notes_text)
        pdf.ln(5)

        # Key Terms Section
        if notes.get("key_terms"):
            pdf.add_page()
            pdf.set_font('helvetica', 'B', 12)
            pdf.cell(0, 8, "KEY TERMS", 0, 1)
            pdf.ln(5)
            
            pdf.set_font('helvetica', '', 11)
            for term, definition in notes["key_terms"].items():
                # Clean term and definition for PDF
                clean_term = clean_text_for_pdf(term)
                clean_definition = clean_text_for_pdf(definition)
                pdf.multi_cell(0, 6, f"- {clean_term}: {clean_definition}")
                pdf.ln(3)

        # Examples Section
        if notes.get("examples"):
            pdf.add_page()
            pdf.set_font('helvetica', 'B', 12)
            pdf.cell(0, 8, "EXAMPLES", 0, 1)
            pdf.ln(5)
            
            pdf.set_font('helvetica', '', 11)
            for i, example in enumerate(notes["examples"], 1):
                # Clean example text for PDF
                clean_example = clean_text_for_pdf(example)
                pdf.multi_cell(0, 6, f"{i}. {clean_example}")
                pdf.ln(3)

        # Connections Section
        if notes.get("connections"):
            pdf.add_page()
            pdf.set_font('helvetica', 'B', 12)
            pdf.cell(0, 8, "CONNECTIONS", 0, 1)
            pdf.ln(5)
            
            pdf.set_font('helvetica', '', 11)
            for connection in notes["connections"]:
                # Clean connection text for PDF
                clean_connection = clean_text_for_pdf(connection)
                pdf.multi_cell(0, 6, f"- {clean_connection}")
                pdf.ln(3)

        # Questions Section
        if notes.get("questions"):
            pdf.add_page()
            pdf.set_font('helvetica', 'B', 12)
            pdf.cell(0, 8, "STUDY QUESTIONS", 0, 1)
            pdf.ln(5)
            
            pdf.set_font('helvetica', '', 11)
            for i, question in enumerate(notes["questions"], 1):
                # Clean question text for PDF
                clean_question = clean_text_for_pdf(question)
                pdf.multi_cell(0, 6, f"{i}. {clean_question}")
                pdf.ln(3)

        pdf.output(output_file)
        print(f"📄 PDF generated successfully: {output_file}")
        return output_file
        
    except Exception as e:
        print(f"Error generating PDF: {e}")
        # Return a fallback path or raise the exception
        raise e

def gen_notes(sample_text):
    """Generate notes and return structured content for web display"""
    try:
        # Generate notes using your existing pipeline
        raw_notes = create_notes(sample_text)
        
        # Only attempt PDF generation if we have valid notes
        if raw_notes and raw_notes.get("title") != "Error processing this chunk":
            try:
                pdf_path = export_notes_to_pdf(raw_notes)
                pdf_path = pdf_path.replace("\\", "/")  # Normalize path
                relative_pdf_path = os.path.relpath(pdf_path, start="D:/Downloads/Edumate/static")
            except Exception as pdf_error:
                print(f"PDF generation failed: {pdf_error}")
                relative_pdf_path = ""
        else:
            relative_pdf_path = ""
        
        print("Raw notes: ", raw_notes)
        
        # Transform to web format
        web_content = {
            "title": raw_notes.get("title", "Generated Notes"),
            "pdf_path": relative_pdf_path,
            "sections": {
                "main_notes": raw_notes.get("main_notes", ""),  # Now a single string
                "key_terms": [],
                "examples": [],
                "connections": [],
                "questions": []
            }
        }

        # Process key terms
        web_content["sections"]["key_terms"] = [
            {"term": k, "definition": v}
            for k, v in raw_notes.get("key_terms", {}).items()
        ]

        # Process other sections
        web_content["sections"]["examples"] = [
            {"text": example} for example in raw_notes.get("examples", [])
        ]
        
        web_content["sections"]["connections"] = [
            {"text": connection} for connection in raw_notes.get("connections", [])
        ]
        
        web_content["sections"]["questions"] = [
            {"text": question} for question in raw_notes.get("questions", [])
        ]

        print("Web content: ", web_content)
        return web_content

    except Exception as e:
        print(f"Error generating notes: {e}")
        return {
            "error": True,
            "message": "Failed to generate notes",
            "details": str(e),
            "title": "Error",
            "pdf_path": "",
            "sections": {
                "main_notes": "",
                "key_terms": [],
                "examples": [],
                "connections": [],
                "questions": []
            }
        }