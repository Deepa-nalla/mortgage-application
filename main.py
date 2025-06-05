import json
import re
import os
import tempfile
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Request
from pydantic import BaseModel
from dotenv import load_dotenv
import google.generativeai as genai
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import whisper

# Load environment variables
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Configure Gemini
genai.configure(api_key=GOOGLE_API_KEY)

# Initialize FastAPI app
app = FastAPI()

# Load Whisper model with support for Git installation
try:
    print("Loading Whisper model...")
    import os
    import sys
    
    # Add potential Git installation path to Python path
    whisper_git_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "whisper"))
    if os.path.exists(whisper_git_path) and whisper_git_path not in sys.path:
        print(f"Adding Git Whisper path to sys.path: {whisper_git_path}")
        sys.path.append(whisper_git_path)
    
    # Import whisper after path adjustment
    import whisper
    
    # Check model cache directory
    cache_dir = os.path.join(os.path.expanduser("~"), ".cache", "whisper")
    print(f"Checking Whisper cache directory: {cache_dir}")
    if os.path.exists(cache_dir):
        print(f"Cache directory exists. Contents: {os.listdir(cache_dir)}")
    else:
        print("Cache directory does not exist yet. It will be created.")
    
    # Load the model with explicit cache directory
    whisper_model = whisper.load_model("base", download_root=cache_dir)
    print(f"Whisper model loaded successfully: {type(whisper_model)}")
except Exception as e:
    print(f"Error loading Whisper model: {str(e)}")
    import traceback
    traceback.print_exc()
    whisper_model = None

# Input schema
class Transcript(BaseModel):
    transcript: str

@app.get("/")
async def root():
    return {"message": "FormsiQ API"}

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail} if isinstance(exc.detail, str) else exc.detail
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=400,
        content={"error": "Invalid input format", "details": str(exc)}
    )

# Helper function for transcription (not an endpoint)
async def transcribe_audio_helper(file_content, filename, language="en"):
    """
    Transcribe an audio file to text using OpenAI's Whisper model.
    This is a helper function, not an endpoint.
    """
    temp_file_path = None
    
    try:
        print("Starting transcription process...")
        print(f"Input filename: {filename}")
        print(f"Language: {language}")
        
        # Check if file has WAV extension
        if not filename.lower().endswith('.wav'):
            print("Error: File is not a WAV file")
            return {
                "error": "Only WAV files are supported",
                "details": "Please convert your audio to WAV format before uploading."
            }
        
        # Create a temporary file in the current directory
        current_dir = os.path.abspath(os.path.dirname(__file__))
        temp_file_name = f"temp_audio_{os.urandom(8).hex()}.wav"
        temp_file_path = os.path.join(current_dir, temp_file_name)
        
        print(f"Creating temporary file at: {temp_file_path}")
        
        # Write the file content to the temporary file
        with open(temp_file_path, 'wb') as f:
            f.write(file_content)
            f.flush()  # Ensure data is written to disk
        
        # Double-check file exists and has content
        if not os.path.exists(temp_file_path):
            print(f"Error: Temporary file not created at {temp_file_path}")
            return {
                "error": "Failed to create temporary file",
                "details": "Could not save the audio file for processing"
            }
        
        file_size = os.path.getsize(temp_file_path)
        print(f"File size: {file_size} bytes")
        
        if file_size == 0:
            print("Error: File is empty")
            return {
                "error": "Empty audio file",
                "details": "The uploaded audio file is empty"
            }
        
        # Ensure the Whisper model is initialized
        global whisper_model
        if whisper_model is None:
            print("Initializing Whisper model...")
            try:
                whisper_model = whisper.load_model("base")
                print("Whisper model loaded successfully")
            except Exception as model_error:
                print(f"Error loading Whisper model: {str(model_error)}")
                return {
                    "error": "Failed to load Whisper model",
                    "details": str(model_error)
                }
        
        try:
            print("Starting transcription with Whisper...")
            # Try direct transcription first
            result = whisper_model.transcribe(
                temp_file_path,
                language=language if language != "auto" else None,
                fp16=False
            )
            
            transcript = result["text"].strip()
            print(f"Transcription successful. First 50 chars: {transcript[:50]}...")
            
            return {
                "transcript": transcript,
                "language": language
            }
            
        except Exception as transcribe_error:
            print(f"Error during transcription: {str(transcribe_error)}")
            import traceback
            traceback.print_exc()
            
            return {
                "error": "Transcription failed",
                "details": str(transcribe_error)
            }
            
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "error": "An unexpected error occurred",
            "details": str(e)
        }
    finally:
        # Clean up the temporary file
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
                print(f"Temporary file deleted: {temp_file_path}")
            except Exception as cleanup_error:
                print(f"Failed to delete temporary file: {str(cleanup_error)}")

@app.post("/extract-fields")
async def extract_fields(
    request: Request,
    file: UploadFile = File(None),
    transcript_text: str = Form(None),
    language: str = Form("en")
):
    """
    Extract mortgage application fields from either an uploaded audio file or a provided transcript.
    If an audio file is provided, it will be transcribed first.
    """
    try:
        # Check if we have either a file or transcript text
        if file is None and not transcript_text:
            return JSONResponse(
                status_code=400,
                content={"error": "Either an audio file or transcript text must be provided"}
            )
            
        # If a file is provided, transcribe it first
        if file:
            # Read the file content
            content = await file.read()
            
            # Call the helper function for transcription
            transcription_result = await transcribe_audio_helper(content, file.filename, language)
            
            # Check if transcription was successful
            if "error" in transcription_result:
                return JSONResponse(
                    status_code=500,
                    content=transcription_result
                )
                
            # Get the transcript text
            transcript_text = transcription_result["transcript"]
            
            # If the client only wants transcription, check for a query parameter
            transcription_only = request.query_params.get("transcription_only", "").lower() == "true"
            if transcription_only:
                return transcription_result
        
        # Store the transcript for later use in error responses
        original_transcript = transcript_text
        
        # Basic validation for empty text
        if not transcript_text or not transcript_text.strip():
            return JSONResponse(
                status_code=400,
                content={
                    "error": "Invalid input format",
                    "details": "Empty text is not a valid transcript",
                    "transcript": original_transcript
                }
            )
        
        # Check if transcript is too short
        words = transcript_text.strip().split()
        if len(words) < 5:
            return JSONResponse(
                status_code=400,
                content={
                    "error": "Invalid input format",
                    "details": "Transcript is too short",
                    "transcript": original_transcript
                }
            )

        # Initialize the model
        model = genai.GenerativeModel("gemini-1.5-flash-latest")
        
        # First, evaluate if the transcript contains sufficient mortgage information
        evaluation_prompt = f"""
        Evaluate if this transcript contains sufficient information for a mortgage application.
        
        A complete mortgage application transcript should include:
        1. Loan amount (a specific dollar amount)
        2. Property information (a specific address or property description)
        3. Loan purpose (purchase, refinance, etc.)
        
        Respond with a JSON object containing:
        1. "is_complete": true/false
        2. "missing_elements": array of missing critical elements
        3. "is_mortgage_related": true/false
        
        Transcript: {transcript_text}
        """
        
        # Make the API call to Gemini for evaluation
        evaluation_response = model.generate_content(evaluation_prompt)
        evaluation_text = evaluation_response.text.strip()
        
        # Extract JSON from the response
        json_match = re.search(r'(\{.*\})', evaluation_text, re.DOTALL)
        if json_match:
            evaluation_text = json_match.group(0)
        
        try:
            evaluation_data = json.loads(evaluation_text)
            
            # Check if the transcript is mortgage-related
            if not evaluation_data.get("is_mortgage_related", False):
                return JSONResponse(
                    status_code=400,
                    content={
                        "error": "Invalid input format",
                        "details": "Transcript doesn't appear to be mortgage-related",
                        "transcript": original_transcript
                    }
                )
            
            # Check if the transcript has sufficient information
            if not evaluation_data.get("is_complete", False):
                missing = evaluation_data.get("missing_elements", [])
                missing_str = ", ".join(missing) if missing else "critical information"
                return JSONResponse(
                    status_code=400,
                    content={
                        "error": "Invalid input format",
                        "details": f"Transcript lacks {missing_str}",
                        "transcript": original_transcript
                    }
                )
                
        except (json.JSONDecodeError, KeyError) as e:
            # If evaluation fails, fall back to extracting fields directly
            print(f"Evaluation parsing failed: {str(e)}. Falling back to direct extraction.")
        
        # Extract fields using Gemini
        extraction_prompt = f"""
        Extract fields relevant to a Uniform Residential Loan Application (Form 1003) from this call transcript.
        Focus on these key sections from the 1003 Form:
        1. Borrower Information (name, DOB, SSN, phone, address)
        2. Employment Information (employer, position, years, income)
        3. Loan Information (loan amount, purpose, property type)
        4. Property Information (address, value, type)
        5. Financial Information (assets, liabilities)
        
        Return them as a list of JSON objects with 'field_name', 'field_value', and 'confidence_score' (0 to 1).
        
        For confidence scoring, follow these guidelines:
        - Assign 1.0 only when the information is explicitly stated with no ambiguity
        - Assign 0.8-0.9 when the information is clearly implied but not explicitly stated
        - Assign 0.6-0.7 when the information is probably correct but could have multiple interpretations
        - Assign 0.4-0.5 when the information is inferred with significant uncertainty
        - Assign 0.1-0.3 when the information is a guess based on limited context
        
        Format your response as a valid JSON array without any explanatory text before or after.
        
        Transcript: {transcript_text}
        """

        # Make the API call to Gemini for field extraction
        extraction_response = model.generate_content(extraction_prompt)
        extraction_text = extraction_response.text.strip()
        
        # Try to extract JSON from the response if it's wrapped in text
        json_match = re.search(r'(\[.*\]|\{.*\})', extraction_text, re.DOTALL)
        if json_match:
            extraction_text = json_match.group(0)
        
        # Safely parse the JSON response
        try:
            extracted_fields = json.loads(extraction_text)
            
            # Check if we got any fields
            if len(extracted_fields) == 0:
                return JSONResponse(
                    status_code=400,
                    content={
                        "error": "Invalid input format",
                        "details": "No fields could be extracted from the transcript",
                        "transcript": original_transcript
                    }
                )
            
            # Check if critical fields are present with reasonable confidence
            has_loan_amount = False
            has_property_info = False
            has_loan_purpose = False
            
            for field in extracted_fields:
                field_name = field.get("field_name", "").lower()
                confidence = field.get("confidence_score", 0)
                
                if "loan amount" in field_name and confidence > 0.5:
                    has_loan_amount = True
                elif any(term in field_name for term in ["property address", "property location"]) and confidence > 0.5:
                    has_property_info = True
                elif "loan purpose" in field_name and confidence > 0.5:
                    has_loan_purpose = True
            
            # If missing critical fields with good confidence, reject the transcript
            missing_fields = []
            if not has_loan_amount:
                missing_fields.append("loan amount")
            if not has_property_info:
                missing_fields.append("property information")
            if not has_loan_purpose:
                missing_fields.append("loan purpose")
                
            if missing_fields:
                return JSONResponse(
                    status_code=400,
                    content={
                        "error": "Invalid input format",
                        "details": f"Transcript lacks {', '.join(missing_fields)}",
                        "transcript": original_transcript
                    }
                )
                
            # Return both the transcript and extracted fields in the required format
            return {
                "transcript": original_transcript,
                "fields": extracted_fields
            }
                
        except json.JSONDecodeError as e:
            # If JSON parsing fails, return a more informative error
            return JSONResponse(
                status_code=400,
                content={
                    "error": "Failed to parse AI response as JSON",
                    "details": str(e),
                    "transcript": original_transcript
                }
            )

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "error": f"An error occurred during processing: {str(e)}",
                "transcript": transcript_text if transcript_text else None
            }
        )

@app.post("/process-audio")
async def process_audio(
    request: Request,  # Add the Request parameter here
    file: UploadFile = File(...),
    language: str = Form("en")
):
    """
    Process an audio file: transcribe it using Whisper and then extract mortgage fields.
    This is a convenience endpoint that combines transcription and field extraction.
    """
    try:
        # First transcribe the audio
        # Read the file content
        content = await file.read()
        
        # Call the helper function for transcription
        transcription_result = await transcribe_audio_helper(content, file.filename, language)
        
        # Check if transcription was successful
        if "error" in transcription_result:
            return JSONResponse(
                status_code=500,
                content=transcription_result
            )
        
        # Now extract fields from the transcript
        transcript_text = transcription_result["transcript"]
        
        # Call extract_fields with the transcript text and pass the request parameter
        extraction_result = await extract_fields(
            request=request,  # Pass the request parameter here
            file=None,
            transcript_text=transcript_text,
            language=language
        )
        
        # Return the result
        return extraction_result
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"error": f"An error occurred during processing: {str(e)}"}
        )
