import requests
import json
import re
import os
from typing import List, Dict, Any
from fpdf import FPDF

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

def chunk_text(text: str, chunk_size: int = 4000) -> List[str]:
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
        return response.json()['response'].strip()
    except Exception as e:
        print(f"Error extracting title: {e}")
        return "Untitled Document"

def generate_summary_for_chunk(chunk: str, level: str = "detailed") -> str:
    """
    Generate a summary for a text chunk using Qwen, with different levels of detail.
    
    Args:
        chunk: Text chunk to summarize
        level: Summary detail level ("concise", "detailed", or "comprehensive")
        
    Returns:
        String containing the generated summary
    """
    # Set length guidance based on desired summary level
    if level == "concise":
        length_guide = "2-3 sentences (approx. 30-40 words)"
    elif level == "detailed":
        length_guide = "4-10 sentences (approx. 70-100 words)"
    else:  # comprehensive
        length_guide = "11-20 sentences (approx. 150-200 words)"

    prompt = f"""Summarize the following content in {length_guide}.
Focus on key information, main ideas, and significant details.
Avoid opinions or additions.

Content to summarize:
{chunk}

Summary:"""

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
        return clean_markdown(response.json()['response'].strip())
    except Exception as e:
        print(f"Error generating summary: {e}")
        return f"Failed to generate {level} summary for this section."

def create_summary(text: str, level: str = "detailed", chunk_size: int = 4000) -> Dict[str, Any]:
    """
    Process text input and generate summary with specified level of detail.
    For long texts, chunks the content and processes each chunk separately.
    
    Args:
        text: Input text to process
        level: Summary detail level ("concise", "detailed", or "comprehensive")
        chunk_size: Maximum size of chunks for processing
        
    Returns:
        Dictionary containing the generated summary
    """
    # Extract title from the beginning of the text
    title = extract_title(text)

    # Chunk the text if it's long
    chunks = chunk_text(text, chunk_size)
    print(f"Processing {len(chunks)} chunks for: {title}")

    # Generate summaries for each chunk
    chunk_summaries = []
    for i, chunk in enumerate(chunks):
        print(f"→ Processing chunk {i + 1}/{len(chunks)}...")
        summary = generate_summary_for_chunk(chunk, level)
        chunk_summaries.append(summary)

    # If there's only one chunk, return its summary directly
    if len(chunks) == 1:
        return {
            "title": title,
            "summary": chunk_summaries[0],
            "chunk_count": 1,
            "summary_level": level
        }

    # For multiple chunks, generate a master summary from all chunk summaries
    combined = " ".join(chunk_summaries)
    master_prompt = f"""Create a cohesive {level} summary from these section summaries of a document titled "{title}".
Make it flow naturally and include all main ideas.

Section summaries:
{combined[:3500]}

Final Summary:"""

    try:
        response = requests.post(
            'http://localhost:11434/api/generate',
            json={
                "model": "qwen2.5:latest",
                "prompt": master_prompt,
                "stream": False,
                "options": {"temperature": 0.3}
            }
        )
        master_summary = clean_markdown(response.json()['response'].strip())
    except Exception as e:
        print(f"Error generating master summary: {e}")
        master_summary = "Failed to generate master summary."

    return {
        "title": title,
        "summary": master_summary,
        "chunk_count": len(chunks),
        "section_summaries": chunk_summaries,
        "summary_level": level
    }

def export_summary_to_pdf(summary_data: Dict[str, Any], output_file: str = None) -> str:
    """
    Export a single summary to a well-formatted PDF.
    
    Args:
        summary_data: Dictionary containing summary information
        output_file: Path where to save the PDF (optional)
        
    Returns:
        Path to the generated PDF file
    """
    title = summary_data.get("title", "Untitled Document")
    if not output_file:
        safe_title = re.sub(r'[\\/*?:"<>|]', "", title)
        safe_title = safe_title.replace(' ', '_')
        output_dir = r"D:\Downloads\Edumate\static\summary"
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, f"{safe_title}_summary.pdf")

    class PDF(FPDF):
        def header(self):
            self.set_font('helvetica', 'B', 14)
            self.cell(0, 10, title, 0, 1, 'C')
            self.ln(5)
            
        def footer(self):
            self.set_y(-15)
            self.set_font('helvetica', 'I', 8)
            self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

    pdf = PDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_left_margin(20)
    pdf.set_right_margin(20)

    # Summary level indicator
    level = summary_data.get("summary_level", "detailed").title()
    pdf.set_font('helvetica', 'B', 12)
    pdf.cell(0, 8, f"{level} Summary", 0, 1)
    pdf.ln(5)

    # Main summary
    pdf.set_font('helvetica', '', 11)
    pdf.multi_cell(0, 6, summary_data.get("summary", "No summary generated."))
    pdf.ln(10)

    # Add section summaries if they exist and there's more than one
    section_summaries = summary_data.get("section_summaries", [])
    if len(section_summaries) > 1:
        pdf.add_page()
        pdf.set_font('helvetica', 'B', 12)
        pdf.cell(0, 8, "Section Summaries", 0, 1)
        pdf.ln(5)
        
        for i, section in enumerate(section_summaries, 1):
            pdf.set_font('helvetica', 'B', 11)
            pdf.cell(0, 6, f"Section {i}", 0, 1)
            pdf.ln(2)
            
            pdf.set_font('helvetica', '', 11)
            pdf.multi_cell(0, 6, section)
            pdf.ln(5)

    pdf.output(output_file)
    print(f"📄 PDF summary generated: {output_file}")
    return output_file

def export_all_summaries_to_pdf(all_summaries: Dict[str, Dict[str, Any]], output_path: str = None) -> str:
    """
    Export all summary levels (concise, detailed, comprehensive) to a combined PDF.
    
    Args:
        all_summaries: Dictionary with keys as summary levels and values as summary data
        output_path: Path where to save the PDF (optional)
        
    Returns:
        Path to the generated PDF file
    """
    # Get title from the first available summary
    title = next(iter(all_summaries.values())).get("title", "Untitled Document")
    
    if not output_path:
        safe_title = re.sub(r'[\\/*?:"<>|]', "", title)
        safe_title = safe_title.replace(' ', '_')
        output_dir = r"D:\Downloads\Edumate\static\summary"
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"{safe_title}_AllSummaries.pdf")

    class PDF(FPDF):
        def header(self):
            self.set_font('helvetica', 'B', 15)
            self.cell(0, 10, title, 0, 1, 'C')
            self.ln(4)

        def footer(self):
            self.set_y(-15)
            self.set_font('helvetica', 'I', 8)
            self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

    pdf = PDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font('helvetica', 'B', 16)
    pdf.cell(0, 10, title, 0, 1, 'C')
    pdf.ln(10)

    # Add each summary level
    for level in ["concise", "detailed", "comprehensive"]:
        summary_data = all_summaries.get(level)
        if not summary_data:
            continue

        pdf.set_font('helvetica', 'B', 14)
        pdf.cell(0, 10, f"{level.title()} Summary", 0, 1, 'L')
        
        pdf.set_font('helvetica', '', 11)
        pdf.multi_cell(0, 6, summary_data.get("summary", ""))
        pdf.ln(8)

        # Add section summaries if appropriate
        section_summaries = summary_data.get("section_summaries", [])
        if len(section_summaries) > 1:
            pdf.set_font('helvetica', 'B', 12)
            pdf.cell(0, 10, "Section Summaries", 0, 1, 'L')
            
            for i, section in enumerate(section_summaries, 1):
                pdf.set_font('helvetica', 'B', 11)
                pdf.cell(0, 8, f"Section {i}", 0, 1)
                
                pdf.set_font('helvetica', '', 11)
                pdf.multi_cell(0, 6, section)
                pdf.ln(3)
                
        pdf.ln(10)

    pdf.output(output_path)
    print(f"📄 Combined PDF generated: {output_path}")
    return output_path

def prepare_web_content(summary_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform summary data into web-friendly format for display.
    
    Args:
        summary_data: Dictionary containing summary information
        
    Returns:
        Dictionary formatted for web display
    """
    web_content = {
        "title": summary_data.get("title", "Generated Summary"),
        "pdf_path": "",  # Will be populated later
        "summary": summary_data.get("summary", ""),
        "level": summary_data.get("summary_level", "detailed"),
        "section_summaries": []
    }
    
    # Process section summaries if they exist
    section_summaries = summary_data.get("section_summaries", [])
    if section_summaries:
        web_content["section_summaries"] = [
            {"text": section} for section in section_summaries
        ]
        
    return web_content

def gen_summary(sample_text: str) -> Dict[str, Any]:
    """
    Generate summaries at different levels (concise, detailed, comprehensive)
    and return structured content for web display.
    
    Args:
        sample_text: Text to summarize
        
    Returns:
        Dictionary containing summary data for web display
    """
    try:
        # Generate a detailed summary as the default
        summary_data = create_summary(sample_text, level="detailed")
        
        # Export to PDF
        pdf_path = export_summary_to_pdf(summary_data)
        
        # Prepare web content
        web_content = prepare_web_content(summary_data)
        web_content["pdf_path"] = os.path.relpath(pdf_path, start="D:/Downloads/Edumate/static").replace("\\", "/")
        
        print(f"✅ Generated summary for: {web_content['title']}")
        return web_content
        
    except Exception as e:
        print(f"Error generating summary: {e}")
        return {
            "error": True,
            "title": "Summary Generation Error",
            "message": "Failed to generate summary",
            "details": str(e)
        }

def auto_summary_gen(content, content_id) -> Dict[str, Any]:
    """
    Generate and store a summary from extracted content.
    
    Args:
        content: Object containing raw text to summarize
        content_id: Identifier for the content
        
    Returns:
        Dictionary containing the web-friendly content
    """
    try:
        # Generate summary using the gen_summary function
        web_content = gen_summary(content.raw_text)
        
        # Create safe filename from title
        safe_title = "".join([c if c.isalnum() else "_" for c in web_content["title"]])
        filename = f"{content_id}_{safe_title}.json"
        
        # Ensure directory exists
        save_folder = os.path.join("D:/Downloads/Edumate/static", 'summary_data')
        os.makedirs(save_folder, exist_ok=True)
        save_path = os.path.join(save_folder, filename)
        
        # Save summary data to JSON file
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(web_content, f, indent=4, ensure_ascii=False)
            
        # Store summary metadata in database (assuming a Summary model exists)
        # Similar to Note model in notes_generator
        """
        summary_entry = Summary(
            content_id=content_id,
            title=web_content["title"],
            file_path=filename
        )
        
        db.session.add(summary_entry)
        db.session.commit()
        """
        
        return web_content
        
    except Exception as e:
        print(f"Summary generation failed: {str(e)}")
        # db.session.rollback()  # Uncomment if using database
        return {
            "error": True,
            "title": "Error",
            "message": "Failed to generate summary",
            "details": str(e)
        }

# Example usage (for testing purposes)
if __name__ == "__main__":
    sample_text = """
    Artificial intelligence (AI) is intelligence demonstrated by machines, as opposed to human or animal intelligence. 
    AI applications include advanced web search engines, recommendation systems, speech recognition, and self-driving cars. 
    
    Machine learning is a method of data analysis that automates analytical model building. It's a branch of artificial intelligence based on the idea that 
    systems can learn from data, identify patterns and make decisions with minimal human intervention.
    
    Deep learning is part of a broader family of machine learning methods based on artificial neural networks with representation learning. Learning can be 
    supervised, semi-supervised or unsupervised.
    """
    
    # Single summary generation
    summary = gen_summary(sample_text)
    print(summary)
    
    # Or generate all summary levels at once
    all_summaries = {}
    for level in ["concise", "detailed", "comprehensive"]:
        print(f"\n🔍 Generating {level.title()} Summary...")
        summary_data = create_summary(sample_text, level=level)
        all_summaries[level] = summary_data
    
    export_all_summaries_to_pdf(all_summaries)