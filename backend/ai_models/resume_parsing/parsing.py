import fitz  # PyMuPDF
import json
import google.generativeai as genai
from dotenv import load_dotenv
import os
import logging
import pytesseract
from PIL import Image
import io
import csv
import concurrent.futures
import time
from threading import Lock
import threading
from tqdm import tqdm

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Global lock for thread-safe operations
csv_lock = Lock()
api_lock = Lock()

def extract_text_from_pdf(pdf_content: bytes) -> str:
    """Extract text from all pages of a PDF file, using OCR when necessary."""
    try:
        doc = fitz.open(stream=pdf_content, filetype="pdf")
        full_text = ""

        for i, page in enumerate(doc):
            page_text = page.get_text("text")

            if not page_text.strip():
                # Render page to an image
                pix = page.get_pixmap(dpi=300)
                img_data = pix.tobytes("png")
                img = Image.open(io.BytesIO(img_data))

                # OCR with pytesseract
                ocr_text = pytesseract.image_to_string(img)
                full_text += ocr_text + "\n"
            else:
                full_text += page_text + "\n"

        doc.close()
        return full_text.strip()

    except Exception as e:
        logger.error(f"Error extracting text from PDF content: {e}")
        return ""

def extract_resume_to_json(resume_text: str, api_key: str) -> dict:
    """Extract structured data from resume text using Gemini."""
    
    # Add rate limiting to prevent API throttling
    with api_lock:
        time.sleep(0.1)  # Small delay between API calls
    
    # Configure Gemini
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-pro')
    
    generation_config = genai.types.GenerationConfig(
        temperature=0.1,
        top_p=0.8,
        top_k=40,
        response_mime_type="application/json",
    )
    
    system_prompt = """
    You are a professional resume extraction agent designed to transform unstructured resume text into a strictly valid JSON object that EXACTLY matches the schema below. Your job is to map any semantically similar or differently named sections in the resume to the closest canonical schema section.

    OUTPUT CONTRACT (CRITICAL):

    Return ONLY a single JSON object (no code fences, no comments, no prose, no trailing commas).

    Follow the exact key names and structure of the provided schema.

    Include ALL fields from the schema, even if empty (use "" for strings and [] for arrays).

    Preserve bullet points as separate array items.

    Escape all quotes inside strings to ensure valid JSON.

    Do not introduce any extra keys or remove any required keys.

    DATE NORMALIZATION:

    Standardize all dates to "MMM YYYY" (e.g., "Jan 2023").

    For ranges, use "MMM YYYY - MMM YYYY" or "MMM YYYY - Present".

    Normalize words like "Ongoing", "Current", "Till Now" to "Present".

    SECTION DIFFERENTIATION (APPLIES EVEN IF THE RESUME MERGES HEADERS):

    Experience = Paid roles, internships, freelance, co-ops.

    Projects = Academic, personal, research, capstone, hackathon projects.

    Positions of Responsibility = Leadership, volunteer roles, committee/club positions.

    CANONICAL SCHEMA TARGETS AND COMMON ALIASES (MAP ALL SIMILAR TERMS TO THESE EXACT KEYS):

    personal_info:
    Aliases: "Contact", "Contact Information", "Reach Me", "Personal Details", "Profile", "About"

    education:
    Aliases: "Academics", "Academic Background", "Qualifications", "Education and Qualifications", "Scholastics"

    experience:
    Aliases: "Work Experience", "Professional Experience", "Employment History", "Industry Experience", "Internships", "Freelance", "Co-op", "Career", "Research Internships"

    projects:
    Aliases: "Technical Projects", "Academic Projects", "Course Projects", "Capstone Projects", "Personal Projects", "Research Projects", "Hackathon Projects"

    positions_of_responsibility:
    Aliases: "Leadership", "Positions of Responsibility", "POR", "Volunteer Experience", "Volunteering", "Committee Roles", "Club Positions", "Community Roles", "Organizing Team"

    technical_skills:
    Aliases: "Skills", "Technical Skills", "Core Competencies", "Tech Stack", "Proficiencies", "Strengths"

    courses_and_certifications:
    Aliases: "Certifications", "Courses", "Online Courses", "Licenses & Certifications", "Relevant Courses"

    achievements_and_awards (This should only contain the scholastic/academic awards and honors for example exam ranks and not work/project awards - those go under experience/projects):
    Aliases: "Awards", "Honors", "Achievements", "Prizes", "Recognitions", "Distinctions"

    extracurriculars:
    Aliases: "Activities", "Co-curricular", "Clubs and Societies", "Student Activities", "Hobbies", "Voluntary Activities"

    publications:
    Aliases: "Publications", "Research Publications", "Papers", "Preprints", "Conference Papers", "Journal Articles"

    DISAMBIGUATION RULES:

    If a section mixes jobs and projects, classify each item individually:

    Paid/contract/internship/freelance roles -> experience

    Course/personal/research/hackathon/capstone -> projects

    "Leadership in a club/committee" -> positions_of_responsibility (not experience)

    "Volunteer service" -> positions_of_responsibility (or extracurriculars if no explicit leadership)

    "Awards/Honors" -> achievements_and_awards, not projects

    "Courses" and "Certifications" -> courses_and_certifications (relevant coursework within education stays under education.relevant_coursework)

    TECHNOLOGIES:

    Extract technologies mentioned in bullet points or lines like "Tech Stack", "Tools", "Skills", or within project/experience descriptions.

    Populate technologies_used lists accordingly without deduplicating across items. Keep original casing.

    MISSING DATA:

    If a field or value is not present in the resume, include the key with "" or [] (as appropriate).

    Do not fabricate data.

    SCHEMA (DO NOT CHANGE):
    {
    "personal_info":
    {
    "name": "string",
    "email": "string",
    "phone": "string",
    "location": "string",
    "linkedin": "string",
    "github": "string",
    "portfolio": "string"
    },
    "education":
    [{
    "degree": "string",
    "field_of_study": "string",
    "institution": "string",
    "location": "string",
    "duration": "string",
    "gpa": "string",
    "relevant_coursework": ["string"],
    "additional_info": "string"
    }],
    "experience":
    [{
    "title": "string",
    "company": "string",
    "location": "string",
    "duration": "string",
    "employment_type": "string",
    "responsibilities": ["string"],
    "achievements": ["string"],
    "technologies_used": ["string"]
    }],
    "projects":
    [{
    "title": "string",
    "organization": "string",
    "duration": "string",
    "project_type": "string",
    "description": "string",
    "key_points": ["string"],
    "technologies_used": ["string"],
    "links": {
    "github": "string",
    "demo": "string",
    "other": "string"
    }
    }],
    "positions_of_responsibility":
    [{
    "title": "string",
    "organization": "string",
    "duration": "string",
    "responsibilities": ["string"],
    "achievements": ["string"]
    }],
    "technical_skills":
    {
    "programming_languages": ["string"],
    "frameworks_libraries": ["string"],
    "databases": ["string"],
    "tools_technologies": ["string"],
    "cloud_platforms": ["string"],
    "other_skills": ["string"]
    },
    "courses_and_certifications":
    [{
    "title": "string",
    "issuing_organization": "string",
    "completion_date": "string",
    "credential_id": "string",
    "description": "string"
    }],
    "achievements_and_awards":
    [{
    "title": "string",
    "issuing_organization": "string",
    "date": "string",
    "description": "string"
    }],
    "extracurriculars":
    [{
    "activity": "string",
    "organization": "string",
    "duration": "string",
    "description": "string",
    "role": "string"
    }],
    "publications":
    [{
    "title": "string",
    "authors": ["string"],
    "publication_venue": "string",
    "publication_date": "string",
    "description": "string"
    }]
    }

    Return ONLY the JSON object with no additional text.
    """

    prompt = f"{system_prompt}\n\nResume Text to Extract:\n{resume_text}"

    try:
        response = model.generate_content(prompt, generation_config=generation_config)
        
        if not response.text:
            logger.warning("Empty response from Gemini API")
            return {}
        
        # Parse the JSON response
        result = json.loads(response.text)
        return result
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON response: {e}")
        logger.error(f"Response text: {response.text[:500]}...")
        return {}
    except Exception as e:
        logger.error(f"Error with Gemini API: {e}")
        return {}

def process_resume(pdf_content: bytes, api_key: str = None) -> dict:
    """
    Main function to process resume PDF to JSON.
    
    Args:
        pdf_content (bytes): The content of the PDF resume file
        api_key (str): Gemini API key (optional, can be set via environment variable)
        
    Returns:
        dict: Structured JSON data extracted from the resume
    """
    # Load environment variables
    load_dotenv()
    
    # Use provided API key or get from environment
    if not api_key:
        api_key = os.getenv('GEMINI_API_KEY')
    
    if not api_key:
        raise ValueError("GEMINI_API_KEY must be provided either as parameter or environment variable")
    
    # Extract text from PDF
    resume_text = extract_text_from_pdf(pdf_content)
    if not resume_text:
        logger.warning(f"No text extracted from PDF content.")
        return {}
    
    # Convert to JSON using Gemini
    json_data = extract_resume_to_json(resume_text, api_key)
    
    return json_data

def main():
    """Main function to process a single PDF resume with detailed logging."""
    import sys
    import traceback
    
    try:
        # Configure detailed logging
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler('resume_processing.log', mode='w')
            ]
        )
        
        logger.info("="*80)
        logger.info("STARTING RESUME PROCESSING")
        logger.info("="*80)
        
        # Specify PDF file path directly here
        pdf_file_path = 'synthetic_resume.pdf'  # Replace with your actual PDF path
        
        # Alternative: Ask user for input
        # pdf_file_path = input("Enter the path to your PDF resume: ").strip()
        
        logger.info(f"Target PDF file: {pdf_file_path}")
        
        # Check if file exists
        if not os.path.exists(pdf_file_path):
            logger.error(f"PDF file does not exist: {pdf_file_path}")
            logger.error(f"Current working directory: {os.getcwd()}")
            
            # List available PDF files in current directory
            pdf_files = [f for f in os.listdir('.') if f.lower().endswith('.pdf')]
            if pdf_files:
                logger.info(f"Available PDF files in current directory: {pdf_files}")
                print(f"Available PDF files: {pdf_files}")
            else:
                logger.warning("No PDF files found in current directory")
                print("No PDF files found in current directory")
            return
        
        # Get file info
        file_size = os.path.getsize(pdf_file_path)
        logger.info(f"PDF file found: {pdf_file_path}")
        logger.info(f"File size: {file_size} bytes ({file_size/1024:.2f} KB)")
        
        # Load environment variables
        logger.info("Loading environment variables...")
        load_dotenv()
        
        # Check API key
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            logger.error("GEMINI_API_KEY not found in environment variables")
            logger.error("Please set GEMINI_API_KEY in your .env file or environment")
            print("Error: GEMINI_API_KEY not found. Please set it in your .env file.")
            return
        else:
            logger.info(f"API key found (length: {len(api_key)})")
        
        # Read PDF file
        logger.info("Reading PDF file...")
        try:
            with open(pdf_file_path, 'rb') as file:
                pdf_content = file.read()
            logger.info(f"Successfully read PDF content: {len(pdf_content)} bytes")
        except Exception as e:
            logger.error(f"Failed to read PDF file: {e}")
            logger.error(f"Error type: {type(e).__name__}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            print(f"Error reading PDF file: {e}")
            return
        
        # Extract text from PDF
        logger.info("Starting PDF text extraction...")
        try:
            resume_text = extract_text_from_pdf(pdf_content)
            logger.info(f"Text extraction completed. Length: {len(resume_text)} characters")
            
            if resume_text:
                # Log first 500 characters of extracted text
                preview = resume_text[:500].replace('\n', '\\n')
                logger.info(f"Text preview: {preview}...")
                
                # Count lines and words
                lines = resume_text.count('\n')
                words = len(resume_text.split())
                logger.info(f"Text statistics - Lines: {lines}, Words: {words}")
                print(f"Extracted {len(resume_text)} characters of text")
            else:
                logger.warning("No text extracted from PDF")
                print("Warning: No text could be extracted from the PDF")
                return
                
        except Exception as e:
            logger.error(f"PDF text extraction failed: {e}")
            logger.error(f"Error type: {type(e).__name__}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            print(f"Error extracting text from PDF: {e}")
            return
        
        # Process resume with Gemini
        logger.info("Starting Gemini API processing...")
        print("Processing with Gemini AI...")
        try:
            json_data = extract_resume_to_json(resume_text, api_key)
            logger.info("Gemini API processing completed")
            
            if json_data:
                logger.info(f"JSON data keys: {list(json_data.keys())}")
                
                # Log section summary
                for section, data in json_data.items():
                    if isinstance(data, list):
                        logger.info(f"Section '{section}': {len(data)} items")
                    elif isinstance(data, dict):
                        logger.info(f"Section '{section}': {len(data)} fields")
                    else:
                        logger.info(f"Section '{section}': {type(data).__name__}")
            else:
                logger.warning("Empty JSON data returned from Gemini API")
                print("Warning: No data extracted by Gemini API")
                return
                
        except Exception as e:
            logger.error(f"Gemini API processing failed: {e}")
            logger.error(f"Error type: {type(e).__name__}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            print(f"Error processing with Gemini API: {e}")
            return
        
        # Save results
        output_file = f"{os.path.splitext(os.path.basename(pdf_file_path))[0]}_parsed.json"
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)
            logger.info(f"Results saved to: {output_file}")
            print(f"Results saved to: {output_file}")
        except Exception as e:
            logger.error(f"Failed to save results: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            print(f"Error saving results: {e}")
        
        # Print summary
        logger.info("="*80)
        logger.info("PROCESSING SUMMARY")
        logger.info("="*80)
        logger.info(f"Input file: {pdf_file_path}")
        logger.info(f"Output file: {output_file}")
        logger.info(f"Text extracted: {len(resume_text)} characters")
        logger.info(f"JSON sections: {len(json_data)}")
        logger.info("Processing completed successfully!")
        
        print("\n" + "="*50)
        print("PROCESSING COMPLETED SUCCESSFULLY!")
        print("="*50)
        
        # Print some key results to console
        if 'personal_info' in json_data:
            name = json_data['personal_info'].get('name', 'N/A')
            email = json_data['personal_info'].get('email', 'N/A')
            print(f"Name: {name}")
            print(f"Email: {email}")
        
        if 'education' in json_data and json_data['education']:
            print(f"Education entries: {len(json_data['education'])}")
            
        if 'experience' in json_data and json_data['experience']:
            print(f"Experience entries: {len(json_data['experience'])}")
            
        if 'projects' in json_data and json_data['projects']:
            print(f"Project entries: {len(json_data['projects'])}")
        
        if 'technical_skills' in json_data and json_data['technical_skills']:
            prog_langs = json_data['technical_skills'].get('programming_languages', [])
            if prog_langs:
                print(f"Programming languages: {', '.join(prog_langs)}")
        
    except Exception as e:
        logger.error("="*80)
        logger.error("FATAL ERROR IN MAIN FUNCTION")
        logger.error("="*80)
        logger.error(f"Error: {e}")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        print(f"Fatal error: {e}")
        return
