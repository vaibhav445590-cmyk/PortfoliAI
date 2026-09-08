import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

if __name__ == "__main__":
    client = OpenAI(
        api_key=os.getenv("OPENAI_API_KEY")
    )

    response = client.responses.create(
        model="gpt-5.5",
        input="Say exactly: PortfoliAI AI connection successful!"
    )

    print(response.output_text)