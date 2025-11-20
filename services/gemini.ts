import { GoogleGenAI } from "@google/genai";

// Initialize the client safely
const apiKey = process.env.API_KEY || '';
const ai = new GoogleGenAI({ apiKey });

export const generateArticleSummary = async (title: string, source: string): Promise<string> => {
  try {
    if (!apiKey) {
      // Fallback for demo purposes if no key is present in environment
      return "API Key missing. Please configure process.env.API_KEY to generate real summaries.";
    }

    const model = 'gemini-2.5-flash';
    const prompt = `
      Provide a "TL;DR" (Too Long; Didn't Read) summary for a tech article with the title: "${title}" from source: "${source}".
      
      Format requirements:
      - Return 3 bullet points.
      - Keep it concise and informative.
      - Use plain text (no markdown symbols like ** or #).
      - Tone: Professional tech news brief.
    `;

    const response = await ai.models.generateContent({
      model: model,
      contents: prompt,
    });

    return response.text || "Could not generate summary.";
  } catch (error) {
    console.error("Gemini API Error:", error);
    throw new Error("Failed to generate summary");
  }
};