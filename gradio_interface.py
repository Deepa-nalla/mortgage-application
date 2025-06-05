import gradio as gr
import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API endpoint (change if your API is hosted elsewhere)
API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
# Custom CSS for styling
custom_css = """
.container {
    max-width: 1000px;
    margin: auto;
    padding: 1rem;
}
.title {
    text-align: center;
    color: #2c3e50;
    margin-bottom: 1rem;
}
.subtitle {
    color: #34495e;
    margin-bottom: 1rem;
    font-size: 1.2em;
    font-weight: bold;
}
.transcript-section {
    margin: 1rem 0;
}
.transcript {
    background-color: #f8f9fa;
    padding: 1rem;
    border-radius: 4px;
    border: 1px solid #dee2e6;
    font-size: 1.1em;
    line-height: 1.5;
    white-space: pre-wrap;
    margin-bottom: 1rem;
}
.confidence-high {
    color: #27ae60 !important;
    font-weight: bold !important;
}
.confidence-medium {
    color: #f39c12 !important;
    font-weight: bold !important;
}
.confidence-low {
    color: #e74c3c !important;
    font-weight: bold !important;
}
.field-name {
    font-weight: bold;
}
.error-message {
    color: #e74c3c !important;
    font-weight: bold !important;
    padding: 1rem !important;
    background-color: #fee !important;
    border-radius: 4px !important;
    margin: 1rem 0 !important;
    border: 1px solid #e74c3c !important;
}
.instructions {
    background-color: #f8f9fa;
    padding: 1rem;
    border-radius: 5px;
    margin-top: 1rem;
}

/* Additional styles for table */
table {
    width: 100%;
    border-collapse: collapse;
    margin: 1rem 0;
}

th, td {
    padding: 8px;
    text-align: left;
    border-bottom: 1px solid #ddd;
}

th {
    background-color: #f8f9fa;
    font-weight: bold;
}
"""

def process_audio(audio_file, language="en"):
    """
    Send the audio file to the API for processing
    """
    if audio_file is None:
        return "<div class='container'><p class='error-message'>Please upload an audio file.</p></div>"
    
    try:
        # Prepare the file for upload
        files = {
               'file': ('recording.wav', open(audio_file, 'rb'), 'audio/wav')
        }
        data = {
              'language': language
        }

        try:
            # Call the API
            response = requests.post(f"{API_URL}/process-audio", files=files)
            response_data = response.json()
            
            # Create a formatted output
            output = "<div class='container'>"
            
            # Always show transcript if available
            transcript = response_data.get("transcript")
            if transcript:
                output += "<div class='transcript-section'>"
                output += "<h2 class='subtitle'>Speech to Text Result</h2>"
                output += f"<div class='transcript'>{transcript}</div>"
                output += "</div>"
            
            # If there's an error, show it
            if "error" in response_data:
                error_msg = response_data.get("error")
                details = response_data.get("details", "")
                output += "<div class='error-message'>"
                output += f"<p><strong>Error:</strong> {error_msg}</p>"
                if details:
                    output += f"<p><strong>Details:</strong> {details}</p>"
                output += "</div>"
            
            # If there are fields, show them
            fields = response_data.get("fields", [])
            if fields:
                output += "<h2 class='subtitle'>Extracted Fields</h2>"
                output += "<table width='100%' style='border-collapse: collapse;'>"
                output += "<tr><th style='text-align: left; padding: 8px; border-bottom: 1px solid #ddd;'>Field</th>"
                output += "<th style='text-align: left; padding: 8px; border-bottom: 1px solid #ddd;'>Value</th>"
                output += "<th style='text-align: left; padding: 8px; border-bottom: 1px solid #ddd;'>Confidence</th></tr>"
                
                for field in fields:
                    name = field.get("field_name", "Unknown")
                    value = field.get("field_value", "Not found")
                    confidence = field.get("confidence_score", 0)
                    
                    # Format confidence as percentage
                    confidence_pct = f"{confidence * 100:.1f}%"
                    
                    # Add color coding based on confidence
                    if confidence >= 0.8:
                        confidence_class = "confidence-high"
                        confidence_icon = "🟢"
                    elif confidence >= 0.5:
                        confidence_class = "confidence-medium"
                        confidence_icon = "🟡"
                    else:
                        confidence_class = "confidence-low"
                        confidence_icon = "🔴"
                    
                    output += f"<tr style='border-bottom: 1px solid #ddd;'>"
                    output += f"<td style='padding: 8px;'><span class='field-name'>{name}</span></td>"
                    output += f"<td style='padding: 8px;'>{value}</td>"
                    output += f"<td style='padding: 8px;'><span class='{confidence_class}'>{confidence_icon} {confidence_pct}</span></td>"
                    output += "</tr>"
                
                output += "</table>"
            
            output += "</div>"
            return output
            
        except requests.exceptions.RequestException as e:
            return f"<div class='container'><p class='error-message'>Network Error: {str(e)}</p></div>"
        
    except Exception as e:
        return f"<div class='container'><p class='error-message'>Error processing request: {str(e)}</p></div>"

def process_text(transcript_text, language="en"):
    """
    Send the transcript text to the API for processing
    """
    if not transcript_text or transcript_text.strip() == "":
        return "<div class='container'><p class='error-message'>Please enter a transcript.</p></div>"
    
    try:
        # Call the API
        response = requests.post(
            f"{API_URL}/extract-fields", 
            data={
                'transcript_text': transcript_text,
                'language': language
            }
        )
        
        # Check if the request was successful
        if response.status_code == 200:
            data = response.json()
            
            # Format the extracted fields for display
            fields = data.get("fields", [])
            
            # Create a formatted output
            output = f"<div class='container'>"
            output += f"<h2 class='subtitle'>Transcript</h2>"
            output += f"<p>{transcript_text}</p>"
            output += f"<h2 class='subtitle'>Extracted Fields</h2>"
            
            if fields:
                # Sort fields by confidence score (highest first)
                fields.sort(key=lambda x: x.get("confidence_score", 0), reverse=True)
                
                output += "<table width='100%' style='border-collapse: collapse;'>"
                output += "<tr><th style='text-align: left; padding: 8px; border-bottom: 1px solid #ddd;'>Field</th>"
                output += "<th style='text-align: left; padding: 8px; border-bottom: 1px solid #ddd;'>Value</th>"
                output += "<th style='text-align: left; padding: 8px; border-bottom: 1px solid #ddd;'>Confidence</th></tr>"
                
                for field in fields:
                    name = field.get("field_name", "Unknown")
                    value = field.get("field_value", "Not found")
                    confidence = field.get("confidence_score", 0)
                    
                    # Format confidence as percentage
                    confidence_pct = f"{confidence * 100:.1f}%"
                    
                    # Add color coding based on confidence
                    if confidence >= 0.8:
                        confidence_class = "confidence-high"
                        confidence_icon = "🟢"
                    elif confidence >= 0.5:
                        confidence_class = "confidence-medium"
                        confidence_icon = "🟡"
                    else:
                        confidence_class = "confidence-low"
                        confidence_icon = "🔴"
                    
                    output += f"<tr style='border-bottom: 1px solid #ddd;'>"
                    output += f"<td style='padding: 8px;'><span class='field-name'>{name}</span></td>"
                    output += f"<td style='padding: 8px;'>{value}</td>"
                    output += f"<td style='padding: 8px;'><span class='{confidence_class}'>{confidence_icon} {confidence_pct}</span></td>"
                    output += "</tr>"
                
                output += "</table>"
            else:
                output += "<p>No fields extracted.</p>"
            
            output += "</div>"
            return output
        else:
            # Handle error responses
            try:
                error_data = response.json()
                error_msg = error_data.get("error", "Unknown error")
                details = error_data.get("details", "No details provided")
                return f"<div class='container'><p class='error-message'>{error_msg}: {details}</p></div>"
            except:
                return f"<div class='container'><p class='error-message'>Error: {response.status_code} - {response.text}</p></div>"
    
    except Exception as e:
        return f"<div class='container'><p class='error-message'>Error processing request: {str(e)}</p></div>"

# Create the Gradio interface
with gr.Blocks(title="FormsiQ - Mortgage Application Extractor", css=custom_css) as demo:
    gr.HTML("<h1 class='title'>FormsiQ - Mortgage Application Extractor</h1>")
    gr.HTML("<p>Extract mortgage application details from audio recordings or text transcripts.</p>")
    
    with gr.Tabs():
        with gr.TabItem("Audio Input"):
            with gr.Row():
                with gr.Column(scale=1):
                    audio_input = gr.Audio(
                        label="Upload or Record Audio",
                        sources=["microphone", "upload"],
                        type="filepath",
                        format="wav"
                    )
                    language_dropdown = gr.Dropdown(
                        choices=["en", "es", "fr", "de", "it", "pt", "nl", "auto"],
                        value="en",
                        label="Language"
                    )
                    process_button = gr.Button("Process Audio", variant="primary")
                
                with gr.Column(scale=2):
                    transcript_output = gr.Textbox(
                        label="Speech to Text Result",
                        lines=3,
                        interactive=False
                    )
                    error_output = gr.HTML(label="Error Messages")
                    results_output = gr.HTML(label="Extracted Fields")
            
            def process_audio_wrapper(audio_path, language):
                if audio_path is None:
                    return "No audio recorded or uploaded.", "<div class='error-message'>Please provide audio input.</div>", None
                
                try:
                    files = {
                        'file': ('recording.wav', open(audio_path, 'rb'), 'audio/wav')
                    }
                    data = {'language': language}
                    
                    response = requests.post(f"{API_URL}/process-audio", files=files, data=data)
                    response_data = response.json()
                    
                    # Get transcript (always try to show it)
                    transcript = response_data.get("transcript", "")
                    
                    # Handle error cases
                    if "error" in response_data:
                        error_msg = response_data.get("error")
                        details = response_data.get("details", "")
                        error_html = f"""
                            <div class='error-message'>
                                <strong>Error:</strong> {error_msg}<br>
                                {f"<strong>Details:</strong> {details}" if details else ""}
                            </div>
                        """
                        return transcript, error_html, None
                    
                    # Format successful results with colored confidence scores
                    fields = response_data.get("fields", [])
                    if fields:
                        results_html = """
                            <div class='container'>
                                <table>
                                    <tr>
                                        <th>Field</th>
                                        <th>Value</th>
                                        <th>Confidence</th>
                                    </tr>
                        """
                        
                        for field in fields:
                            name = field.get("field_name", "Unknown")
                            value = field.get("field_value", "Not found")
                            confidence = field.get("confidence_score", 0)
                            
                            # Add color coding based on confidence
                            if confidence >= 0.8:
                                confidence_class = "confidence-high"
                                confidence_icon = "🟢"
                            elif confidence >= 0.5:
                                confidence_class = "confidence-medium"
                                confidence_icon = "🟡"
                            else:
                                confidence_class = "confidence-low"
                                confidence_icon = "🔴"
                            
                            results_html += f"""
                                <tr>
                                    <td><span class='field-name'>{name}</span></td>
                                    <td>{value}</td>
                                    <td><span class='{confidence_class}'>{confidence_icon} {confidence:.1%}</span></td>
                                </tr>
                            """
                        
                        results_html += """
                            </table>
                        </div>
                        """
                    return transcript, None, results_html
                    
                except Exception as e:
                    return str(e), "<div class='error-message'>Failed to process audio.</div>", None
            
            # Update the click event handler
            process_button.click(
                fn=process_audio_wrapper,
                inputs=[audio_input, language_dropdown],
                outputs=[transcript_output, error_output, results_output]
            )
            
        with gr.TabItem("Text Input"):
            with gr.Row():
                with gr.Column(scale=1):
                    text_input = gr.Textbox(
                        label="Enter Transcript", 
                        placeholder="Enter the mortgage application transcript here...",
                        lines=10
                    )
                    text_language = gr.Dropdown(
                        choices=["en", "es", "fr", "de", "it", "pt", "nl", "auto"], 
                        value="en",
                        label="Language"
                    )
                    text_button = gr.Button("Process Text", variant="primary")
                
                with gr.Column(scale=2):
                    # Add an error output component for text input
                    text_error_output = gr.HTML(label="Error Messages", visible=True)
                    text_output = gr.HTML(label="Results")
            
            def wrapped_process_text(text, lang):
                try:
                    result = process_text(text, lang)
                    if "error-message" in result:
                        return result, None
                    return None, result
                except Exception as e:
                    return f"<div class='container'><p class='error-message'>{str(e)}</p></div>", None
            
            text_button.click(
                fn=wrapped_process_text,
                inputs=[text_input, text_language],
                outputs=[text_error_output, text_output],
                api_name="process_text"
            )
    
    gr.HTML("""
    <div class='instructions'>
        <h3>Sample Transcripts</h3>
        <p>Try these examples:</p>
        <ol>
            <li><strong>Complete Application:</strong> "Hi, my name is John Smith. I'd like to apply for a mortgage loan of $350,000. I'm looking to purchase a single-family home at 123 Main Street. My annual income is $120,000 and I've been employed at Tech Corp for 5 years as a software engineer. My credit score is around 750."</li>
            <li><strong>Refinance Application:</strong> "I'm Robert Johnson calling about refinancing my current mortgage for $300,000. I've owned my home at 789 Oak Drive, Austin, TX for 8 years and the current value is approximately $500,000. I still owe about $300,000 on my mortgage and I'm looking to get a better interest rate."</li>
        </ol>
    </div>
    """)

# Launch the interface
if __name__ == "__main__":
    demo.launch(share=True)  # Set share=False if you don't want to generate a public link
