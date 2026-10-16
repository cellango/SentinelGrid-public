from openai import OpenAI
import httpx


client = OpenAI(
    base_url="http://localhost:8023/v1",
    api_key="unused-in-local-standalone-path",
    http_client=httpx.Client(
        headers={
            "X-Tenant-ID": "11111111-1111-1111-1111-111111111111",
            "X-Realm": "demo",
            "X-App-ID": "demo-app",
        }
    ),
)


response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "user", "content": "Why do AI gateways matter?"}
    ],
)

print(response.choices[0].message.content)
