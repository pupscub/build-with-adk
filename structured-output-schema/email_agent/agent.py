from google.adk.agents import LlmAgent
from pydantic import BaseModel, Field

class EmailContent(BaseModel):
    subject: str = Field(description='The subject line of the email. Keep it concise and descriptive.')
    body: str = Field(description='The main content of the email. Should be well-formatted with proper greetings, paragraphs, and closings.')


root_agent = LlmAgent(
    model='gemini-2.0-flash-lite',
    name='email_agent',
    description='Generates professional emails with a clear subject and well-structured body.',
    output_schema=EmailContent,
    output_key='email',
    instruction=""" You are an Email Generation Assistant.
        Your task is to generate a professional email based on the user's request.
        GUIDELINES:
        1. Ensure the subject is concise and descriptive.
        2. Structure the body with 
            - professional greetings
            - Clear and concise paragraphs
            - A polite closing statement.
            - signature with the sender's name and position.
        3. Use proper grammar and punctuation throughout the email.
        4. Suggest attachments if relevant, but do not include them in the email body.
        5. Email tone should match the purpose and audience (formal for business, friendly for personal, etc.)
        6. Avoid using jargon or overly complex language unless necessary.

        DO NOT include any explanatory text or additional comments outside the email structure.
    """,
)
