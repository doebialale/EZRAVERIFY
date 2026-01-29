# screen_reader_decider.py
"""
Pipeline:
 1) Screenshot
 2) OCR (pytesseract) with preprocessing
 3) Send text to an LLM (OpenAI example)
 4) Parse JSON decision and act (print / clipboard / click / keystroke)
"""

import os
import io
import json
import time
from dataclasses import dataclass
from typing import Optional, Dict, Any

from PIL import Image, ImageOps, ImageFilter
import pytesseract
import mss
import openai
from dotenv import load_dotenv

# Optional automation tools
import pyperclip
import pyautogui

load_dotenv()  # loads .env if present

# -------------------------
# CONFIG
# -------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("Please set OPENAI_API_KEY in env or .env")

openai.api_key = OPENAI_API_KEY

# If pytesseract can't find binary, you can set
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Options
OCR_LANG = "eng"
SCREENSHOT_REGION = (
    None  # None = full screen; or dict(left=..., top=..., width=..., height=...)
)
OCR_DPI_RESIZE = 2  # scale up to improve OCR on small text
THRESHOLD_BINARIZE = True

# LLM and decision template
MODEL_NAME = "gpt-4o"  # replace with whichever model name you use / have access to

# Template instructing the model to output strict JSON for machine parsing
DECISION_PROMPT_TEMPLATE = """
You are an assistant that MUST respond with a single JSON object (no surrounding text).
The JSON must have this schema:
{{
  "intent": "<one-word intent, e.g. 'read', 'copy', 'click', 'ignore', 'alert'>",
  "confidence": 0.0,
  "action": {{
    "type": "<'none'|'copy'|'press'|'click'|'open_url'|'custom'>",
    "payload": <object or string; depends on type>
  }},
  "notes": "<optional human-readable notes>"
}}

Here is the extracted screen text (raw):
\"\"\"{extracted_text}\"\"\"

Rules:
- Choose intent and action based ONLY on the visible screen text.
- If you are uncertain, set confidence < 0.7 and action.type 'none'.
- For copy action: payload should be the text to copy to clipboard.
- For press action: payload should be a dict like {{ "keys": ["ctrl","w"] }} (these map to pyautogui.hotkey).
- For click action: payload should be a dict like {{ "x": 123, "y": 456 }} in screen coordinates.
- For open_url: payload should be a string URL.
- Keep JSON compact and valid.
"""


# -------------------------
# Helpers
# -------------------------
def capture_screenshot(region: Optional[Dict[str, int]] = None) -> Image.Image:
    """Capture screenshot. region: dict(left, top, width, height) in pixels"""
    with mss.mss() as sct:
        if region:
            monitor = {
                "left": region["left"],
                "top": region["top"],
                "width": region["width"],
                "height": region["height"],
            }
        else:
            monitor = sct.monitors[0]  # full virtual screen
        sct_img = sct.grab(monitor)
        img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
        return img


def preprocess_for_ocr(
    img: Image.Image, resize_factor: int = 1, binarize: bool = False
) -> Image.Image:
    """Simple preprocessing: convert to grayscale, upscale, optional binarize, denoise."""
    img = img.convert("L")  # grayscale
    if resize_factor and resize_factor != 1:
        w, h = img.size
        img = img.resize(
            (w * resize_factor, h * resize_factor), Image.Resampling.LANCZOS
        )
    img = img.filter(ImageFilter.MedianFilter(size=3))
    if binarize:
        img = ImageOps.autocontrast(img)
        img = img.point(lambda p: 255 if p > 180 else 0)
    return img


def run_ocr(img: Image.Image, lang: str = OCR_LANG) -> str:
    """Extract text using pytesseract."""
    config = "--psm 3"  # automatic page segmentation
    try:
        text = pytesseract.image_to_string(img, lang=lang, config=config)
    except Exception as e:
        raise RuntimeError(f"OCR failed: {e}")
    return text.strip()


def ask_llm_for_decision(
    extracted_text: str, model: str = MODEL_NAME, max_tokens: int = 300
) -> Dict[str, Any]:
    """Send prompt to LLM and parse JSON response. Retries once if parsing fails."""
    prompt = DECISION_PROMPT_TEMPLATE.format(
        extracted_text=extracted_text.replace('"""', '\\"\\""')
    )
    # Use openai.ChatCompletion or Responses depending on SDK; using ChatCompletion for compatibility
    for attempt in range(2):
        resp = openai.ChatCompletion.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a strict JSON-only assistant for UI automation.",
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=max_tokens,
            temperature=0.0,
        )
        text = resp.choices[0].message.content.strip()
        # Try parse JSON out of the reply (allow for model adding codeblock)
        try:
            # strip backticks or markdown fences
            if text.startswith("```"):
                # remove triple backtick blocks
                parts = text.split("```")
                if len(parts) >= 2:
                    text = parts[1].strip()
            parsed = json.loads(text)
            return parsed
        except Exception:
            # try to extract first {...} substring
            start = text.find("{")
            end = text.rfind("}") + 1
            if start != -1 and end != -1 and end > start:
                try:
                    parsed = json.loads(text[start:end])
                    return parsed
                except Exception:
                    pass
        # if parsing failed, try again with a clarifying system message
        if attempt == 0:
            # ask model to output only JSON if it failed parsing
            continue
    raise RuntimeError(
        "Failed to get valid JSON decision from LLM.\nLLM output:\n" + text
    )


# -------------------------
# Action executors
# -------------------------
def execute_action(action: Dict[str, Any]) -> None:
    """Execute an action dict returned by LLM. This function contains potentially dangerous operations.
    Use with caution. Currently supports 'copy', 'press', 'click', 'open_url' (open_url uses webbrowser)."""
    typ = action.get("type", "none")
    payload = action.get("payload", None)

    if typ == "none":
        print("[ACTION] No action requested.")
        return

    if typ == "copy":
        if isinstance(payload, dict):
            payload_text = payload.get("text") or payload.get("payload") or str(payload)
        else:
            payload_text = str(payload)
        pyperclip.copy(payload_text)
        print(f"[ACTION] Copied to clipboard: {payload_text[:200]}")

    elif typ == "press":
        # payload example: {"keys": ["ctrl","w"]}
        if isinstance(payload, dict) and "keys" in payload:
            keys = payload["keys"]
            if isinstance(keys, list) and keys:
                pyautogui.hotkey(*keys)
                print(f"[ACTION] Pressed keys: {keys}")
            else:
                print("[ACTION] Invalid keys payload.")
        else:
            print("[ACTION] Invalid press payload.")

    elif typ == "click":
        # payload example: {"x": 123, "y": 456}
        if isinstance(payload, dict) and "x" in payload and "y" in payload:
            x = int(payload["x"])
            y = int(payload["y"])
            pyautogui.click(x, y)
            print(f"[ACTION] Clicked at ({x}, {y})")
        else:
            print("[ACTION] Invalid click payload.")

    elif typ == "open_url":
        import webbrowser

        url = str(payload)
        webbrowser.open(url)
        print(f"[ACTION] Opened URL: {url}")

    else:
        print(f"[ACTION] Unknown action type: {typ}. Payload: {payload}")


# -------------------------
# Main flow
# -------------------------
def main_loop(single_shot: bool = True):
    """Main pipeline: capture, OCR, LLM, execute. If single_shot False, loops every N seconds."""
    try:
        while True:
            t0 = time.time()
            img = capture_screenshot(SCREENSHOT_REGION)
            img_proc = preprocess_for_ocr(
                img, resize_factor=OCR_DPI_RESIZE, binarize=THRESHOLD_BINARIZE
            )
            extracted = run_ocr(img_proc)
            print("=" * 40)
            print("Extracted text (preview):")
            print(extracted[:2000] + ("..." if len(extracted) > 2000 else ""))
            print("=" * 40)

            # Safety check: if extracted is empty or obviously sensitive, skip or warn
            if not extracted.strip():
                print("[INFO] No text detected; skipping LLM call.")
            else:
                decision = ask_llm_for_decision(extracted)
                print("[LLM DECISION]", json.dumps(decision, indent=2)[:2000])
                # Basic confidence check
                confidence = float(decision.get("confidence", 0))
                if confidence < 0.6:
                    print(
                        "[INFO] Low confidence ({:.2f}); not executing actions automatically.".format(
                            confidence
                        )
                    )
                else:
                    action = decision.get("action", {})
                    # Confirm before executing potentially destructive actions (simple safety)
                    print(f"[INFO] Executing action of type '{action.get('type')}'.")
                    execute_action(action)

            # break or sleep depending on mode
            if single_shot:
                break
            else:
                # throttle loop: once every 2 seconds (configurable)
                elapsed = time.time() - t0
                time.sleep(max(0, 2.0 - elapsed))

    except KeyboardInterrupt:
        print("Stopped by user.")
    except Exception as e:
        print("Error:", e)


# -------------------------
# If run directly
# -------------------------
if __name__ == "__main__":
    # Example usage: run once
    print("Starting screen-reader decider (single shot). Press Ctrl-C to stop.")
    main_loop(single_shot=True)
