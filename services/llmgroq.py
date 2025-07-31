import httpx
import os 

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
async def query_groq(prompt: str):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "deepseek-r1-distill-llama-70b",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=data)

        try:
            json_data = response.json()
            if "choices" not in json_data:
                print("❌ Error from Groq API:", json_data)
                return "Groq API Error: " + json_data.get("error", {}).get("message", "Unknown error")
            return json_data["choices"][0]["message"]["content"]
        except Exception as e:
            print("❌ Failed to parse response JSON:", response.text)
            raise e
