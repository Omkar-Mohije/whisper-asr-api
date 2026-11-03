// Vercel Serverless Function: Audio Transcription using Whisper Large-v3-Turbo API

export const config = {
  api: {
    bodyParser: false, // Disabling body parser to stream raw multipart file
  },
};

export default async function handler(req, res) {
  // Set CORS headers
  res.setHeader("Access-Control-Allow-Credentials", "true");
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET,OPTIONS,PATCH,DELETE,POST,PUT");
  res.setHeader(
    "Access-Control-Allow-Headers",
    "X-CSRF-Token, X-Requested-With, Accept, Accept-Version, Content-Length, Content-MD5, Content-Type, Date, X-Api-Version, x-api-key, Authorization"
  );

  if (req.method === "OPTIONS") {
    res.status(200).end();
    return;
  }

  if (req.method !== "POST") {
    return res.status(405).json({ error: "Method not allowed. Use POST." });
  }

  const apiKey = req.headers["x-api-key"] || process.env.GROQ_API_KEY;

  if (!apiKey) {
    return res.status(401).json({
      error: "Missing API Key. Set GROQ_API_KEY in Vercel environment variables or enter it in app settings.",
    });
  }

  try {
    const contentType = req.headers["content-type"] || "";
    
    // Forward the incoming audio stream directly to Groq Whisper Large-v3-Turbo
    const groqResponse = await fetch("https://api.groq.com/openai/v1/audio/transcriptions", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${apiKey}`,
        "Content-Type": contentType,
      },
      body: req, // Pipe raw request stream
      duplex: "half",
    });

    const data = await groqResponse.json();

    if (!groqResponse.ok) {
      return res.status(groqResponse.status).json({
        error: data.error?.message || "Whisper API transcription failed",
      });
    }

    return res.status(200).json(data);
  } catch (error) {
    console.error("Transcription error:", error);
    return res.status(500).json({
      error: "Internal server error during audio transcription: " + error.message,
    });
  }
}
