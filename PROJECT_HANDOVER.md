# Kramm AI: "Mom's Teaching Partner" - Handover Documentation

This document serves as the comprehensive state and context guide for transitioning the project to a new development agent (Codex). It contains the architecture overview, recent substantial updates, bug fixes, and pending issues to be resolved.

## 1. Project Overview & Architecture
**Kramm** is an AI-powered parenting and teaching assistant that allows parents to actively guide their child's learning.
- **Frontend (TV Dashboard):** Built in React using Vite. Located in `/tv-dashboard`. Uses Socket.io to sync live with backend events. Runs locally on `localhost:5173`.
- **Backend (Telegram Bot + Server):** Built in Python using FastAPI, `python-telegram-bot`, `python-socketio`, and Gemini API. Located in `/backend`. Runs locally via `python -m backend.main`.
- **Core Loop:** Parent sends a photo of homework via Telegram -> AI extracts the topic -> Parent selects 'Quiz Mode' -> AI generates a quiz -> Dashboard (TV) displays question -> Kid answers -> AI evaluates and gives an explanation tailored for the Mom to easily explain to the kid.

## 2. Recent Version Changes & Enhancements
- **UI/UX Refinement:** 
  - The TV Dashboard has been updated to feature a vertical left-aligned Quiz Progress Track rather than a horizontal one.
  - Evaluation results are now embedded dynamically inside the answer card, rather than disappearing popups.
  - Added a "Scope Assessment Popup" UI that alerts the user if the AI intelligently decided fewer questions were required for a narrow topic.
- **Smart Quiz Generator (`quiz_generator.py`):** 
  - Restructured the Gemini Prompt to natively generate a dual-architecture answer key: `kid_answer` (direct correct answer) and `mom_explanation` (a layman explainer for a 10-year-old concept).
  - The AI prompt now mentally verifies the topic against the NCERT syllabus scope. It dynamically scales the number of questions to a "need-based" limit, up to a maximum of 7 questions.
- **Visualizer Integration (`visual_generator.py`):** 
  - Added a visual diagram generator feature that can be triggered mid-quiz or from the topic list, displaying custom educational illustrations on the TV.

## 3. Critical Bug Fixes Applied
- **WebSocket Desync:** Fixed an issue where the TV was stuck on "Locked" and not receiving Mom's Explanations. This was solved by ensuring `kid_answer` and `mom_explanation` payloads are passed immediately on the first `emit_quiz_question` event.
- **Cache Invalidations:** Forced the quiz state to bypass legacy cached payloads (`cached_questions = None`), correcting a bug where 5-question outdated loops were constantly being fed to the user.
- **WebSocket Emission Conditionals:** Removed strict `session.get("quiz_on_tv")` checks inside Telegram callbacks, allowing the Python bot to successfully push WS updates to the TV screen even if the mobile socket session state became momentarily decoupled.

## 4. Pending Issues & Next Steps (Stuck Processes)
### Integrating Gemini Native Image Generation (HIGHEST PRIORITY)
**The Issue:** Currently, `backend/ai/visual_generator.py` generates images by injecting the AI's descriptive prompt into a public, free-to-use Pollinations AI URL (`https://image.pollinations.ai/prompt/...`). 
**The User Request:** The user explicitly noted that their uploaded Gemini API key *has active billing enabled*. They requested that image generation be handled natively through the Gemini/Google Imagen API rather than relying on Pollinations.
**Action Item for Codex:**
1. Update `visual_generator.py` to utilize `google-generativeai` (or `google-genai` depending on SDK bounds) to hit the `imagen-3.0-generate-001` or Gemini image generation endpoint. 
2. Capture the returned base64/bytes, save the file locally or serve it statically from the FastAPI server.
3. Update the `html_content` payload to embed the native generated image instead of the external URL.

### Dev Quality of Life
- The current backend startup logic in `backend/main.py` uses `uvicorn.run(combined_app)`. It lacks `reload=True`. As a result, Python code changes frequently require the user to manually `taskkill` the terminal to wipe the memory state. Implementing a robust dev-reload logic would streamline testing. 

## 5. Contacting the AI API
Routing calls to Gemini are done primarily through `backend/ai/router.py`. All system prompts are housed in `backend/config.py`. Keyboard callbacks and inline routing heavily reside in `backend/bot/handlers.py` and `backend/bot/keyboards.py`.
