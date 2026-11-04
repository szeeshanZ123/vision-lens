# 🚀 Vision Lens — Deployment Guide

## 1. Production Architecture Overview

Vision Lens uses a serverless full-stack deployment model:
- **Hosting Platform**: Vercel
- **Runtime**: `@vercel/python` Serverless Function
- **Entry File**: `api/index.py` (mapping `/(.*)` routes to FastAPI `app`)
- **Public Domain**: `https://vision-lens-ivory.vercel.app`
- **Dashboard**: `https://vercel.com/szeeshanz123s-projects/vision-lens/6kwDAURymHAeSX8a8jAU654tFfdy`

---

## 2. Setting Required Environment Variables on Vercel

To activate the Gemini Vision AI service on production:

1. Open your [Vercel Project Dashboard](https://vercel.com/szeeshanz123s-projects/vision-lens/6kwDAURymHAeSX8a8jAU654tFfdy).
2. Go to **Settings -> Environment Variables**.
3. Add the following environment variable:
   - **Key**: `GEMINI_API_KEY`
   - **Value**: Your actual Gemini API key from [Google AI Studio](https://aistudio.google.com/app/apikey) (format: `AIzaSy...`)
   - **Environments**: Check `Production`, `Preview`, and `Development`.
4. (Optional) Multimodal Model Selection:
   - **Key**: `GEMINI_MODEL`
   - **Value**: `gemini-2.5-flash`
5. Click **Save**.
6. Trigger a redeploy from the **Deployments** tab by selecting the latest deployment and clicking **Redeploy** (ensure "Use existing Build Cache" is unchecked so the new environment variable is loaded).

---

## 3. Deployment Health Verification

Once redeployed with the environment variable configured:

```bash
curl https://vision-lens-ivory.vercel.app/api/health
```

Expected verified output:
```json
{
  "status": "online",
  "gemini_configured": true,
  "model": "gemini-2.5-flash",
  "message": "Gemini Visual Lens backend is running."
}
```

---

## 4. Local Development Deployment

To run the application locally:

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Copy and configure .env
cp .env.example .env

# 3. Launch server
python app.py
```

Open `http://localhost:8000` in your web browser.
To test from a phone on the same Wi-Fi network, open `http://<YOUR_LOCAL_IP>:8000`.

