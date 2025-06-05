This project automates the extraction of key fields from mortgage-related calls and transcripts, targeting the fields from 'Form 1003 Uniform Residential Loan Application'.


Approach - 
I developed a scalable GenAI-based solution using Python, FastAPI, Gradio, Gemini flash 1.5, OpenAI Whisper. 

Implemented robust validation checks and exception handling at every check point.

Designed simple UI using Gradio for uploading audio/text and viewing extraction results including confidence scores.


Tools & Libraries used - 
AI - Google Gemini 1.5, OpenAI Whisper, Prompt Engineering
Frameworks - FastAPI, Gradio
Libraries - Pydandic, Requests, JSON etc


Flow of the project - 
Users upload either an audio file (such as a customer service call) or a text transcript through a simple Gradio UI. 
If an audio file is provided, it is first transcribed into text using OpenAI’s Whisper model. 
The resulting text, or directly uploaded text, undergoes validation checks to ensure it contains enough relevant information. 
The validated text is then sent to Google’s Gemini 1.5 API, where prompt engineering techniques are used to extract key fields required for the 1003 Uniform Residential Loan Application—including loan amount, property type, and borrower details—along with confidence scores. 
Finally, the extracted fields and corresponding confidence scores are displayed back to the user through the Gradio interface, providing a seamless end-to-end AI-powered solution for automating mortgage form processing.


About GEMINI 1.5 Flash - 
- Lightweight, low-latency, multimodal (text, image, audio)
- Large token limit, confidence scoring
- Optimized for prompt-based extraction  
- Speed & cost efficient for production

About OpenAI Whisper
- Open-source Automatic Speech Recognition (ASR) model
- Excellent for real-world phone calls and domain-specific terminology
- Transcription feeds directly into Gemini for structured extraction


