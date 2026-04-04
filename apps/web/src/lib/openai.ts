import OpenAI from "openai";

export const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

export async function askQuestion(question: string) {
  const response = await openai.chat.completions.create({
    model: "gpt-5.4-mini",
    messages: [{ role: "user", content: question }],
  });
  return response.choices[0].message?.content;
}
