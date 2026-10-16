import OpenAI from "openai";

const client = new OpenAI({
  baseURL: "http://localhost:8023/v1",
  apiKey: "unused-in-local-standalone-path",
  defaultHeaders: {
    "X-Tenant-ID": "11111111-1111-1111-1111-111111111111",
    "X-Realm": "demo",
    "X-App-ID": "demo-app",
  },
});

const response = await client.chat.completions.create({
  model: "gpt-4o-mini",
  messages: [
    { role: "user", content: "Explain how AI gateways help with policy enforcement." },
  ],
});

console.log(response.choices[0].message.content);
