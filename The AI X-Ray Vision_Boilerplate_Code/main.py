import base64, io, json
from io import BytesIO
import streamlit as st
from PIL import Image, ImageDraw, ImageFont
from groq import Groq
import config

st.set_page_config(page_title="The AI X-Ray Vision", page_icon="🧪", layout="centered")

client = Groq(api_key=config.GROQ_API_KEY)
st.session_state.setdefault("xray_outputs", [])

PROMPT = """Analyze this image and return ONLY valid JSON.
Identify all clearly visible important objects in the image.
For each object, return: name, short_label, fun_metadata, confidence, box
The "box" must use percentages 0 to 100 with x, y, w, h.
Rules:
- Include all clearly visible important objects
- Do not guess hidden or unclear objects
- If unsure, skip the object
- Keep labels short and kid-friendly
- Confidence must be one of: high, medium, low
- Never identify a real person by name
- If a person appears, use generic labels like "person", "smiling adult", "child", or "seated person"
- Do not guess identity, age, profession, or relationship
- Return JSON only
Format:
{"scene_title":"short futuristic title","objects":[{"name":"person","short_label":"smiling adult","fun_metadata":"person detected near the center","confidence":"high","box":{"x":20,"y":10,"w":25,"h":60}}]}"""

PERSON_WORDS = {"person", "adult", "child", "woman", "man", "girl", "boy", "human", "people"}
SAFE_LABELS = {"person", "smiling adult", "child", "seated person"}

st.title("🧪 The AI X-Ray Vision")
st.write("Upload a real photo and turn it into AI scanner images.")
st.markdown(
    "This app scans your image, finds important objects, "
    "and creates clean scanner-style images in smaller groups."
)
def analyze_image(file):
    encoded = base64.b64encode(file.getvalue()).decode()
    response = client.chat.completions.create(
        model=config.GROQ_VISION_MODEL,
        messages=[{
            "role": "user",
            "content": [
                {"type": "text","text": PROMPT},
                {"type": "image_url","image_url": {"url":f"data:{file.type};base64,{encoded}"}}

            ],
        }],
        temperature=0.2,
        max_completion_tokens=1000,
        response_format={"type": "json_object"}
    )
    return json.loads(response.choices[0].message.content)
def hud(img, scene, objects, page, total):
    img = img.convert("RGBA")
    overlay = Image.new("RGBA", img.size, (0,0,0,0))
    draw = ImageDraw.Draw(overlay)
    (w,h), (title_font, label_font, small_font) = img.size, fonts()
    green = (57, 255, 20, 255)
    panel = (0, 20, 10, 185)
    red   = (255, 60, 60, 255)
    draw.rectangle((20, 20, w - 20, 70), fill=panel)
    draw.text((35,32), f"[ {scene.upper()} [{page}/{total}]]", fill=green, font=title_font)
    draw.ellipse((w - 120, 28, w - 104, 44), fill=red)
    draw.text((w - 96, 26), "REC", fill=green, font=label_font)
    for obj in objects:
        box = obj.get("box", {})
        if not all (k in box for k in ("x","y","w","h")):
            continue
        x1, y1, x2, y2 = px(box, w, h)
        draw.rectangle((x1,y1,x2,y2), outline=green, width=2)
        for a, b, c, d in [
            (x1, y1, x1+18, y1),(x1, y1, x1, y1+18),
            (x1, y1, x2+18, y1),(x1, y1, x2, y1+18),
            (x1, y1, x1+18, y1),(x1, y1, x1, y2-18),
            (x1, y1, x2+18, y1),(x1, y1, x2, y2-18),
        ]:
            draw.line((a,b,c,d), fill=green, width=3)
        label    = obj.get("short_label", obj.get("name", "UNKNOWN")).upper()
        meta     = obj.get("fun_metadata", "NO DATA")
        conf     = obj.get("confidence", "low").upper()
        panel_y  = max(80, y1 - 55)
        if panel_y < 80:
            panel_y = min(h - 80, y2 + 10)   
        panel_x1 = x1
        panel_x2 = min(w - 20, x1 + 320)     
        panel_y2
def px(box, w, h):
    values = [box["x"], box["y"], box["x"] + box["w"], box["y"] + box["h"]]
    return tuple(max(0, min(int(v * s / 100), s - 1)) for v, s in zip(values, (w, h, w, h)))
def prepare_objects(items):
    seen, output = set(), []
    for item in items:
        name       = item.get("name","").strip().lower()
        label      = item.get("short_label","").strip().lower()
        confidence = item.get("confidence", "low").strip().lower()
        if not name or confidence not in {"high", "medium"}:
            continue
        if any(word in name or word in label for word in PERSON_WORDS):
            item["name"] = "person"
            if label not in SAFE_LABELS:
                item["short_label"] = "person"
        key = (item["name"].strip().lower(), item.get("short_label","").strip().lower()) 
        if key not in seen:
            seen.add(key)
            output.append(item)       
    return output  
def groups(items, size):
    return [items[i:i + size] for i in range(0, len(items), size)]
def fonts():
    try:
        return [ImageFont.truetype("arial.ttf", size) for size in (28,18,14)]
    except Exception:
        return [ImageFont.load_default()] * 3
file = st.file_uploader("Upload a photo", type=["png","jpg","jpeg","webp"]) 
group_size = st.selectbox("Objects per scanner image!", [3,4], index=1) 
if file:
    original = Image.open(BytesIO(file.getvalue()))
    st.image(original, caption="Original imagee", use_container_width=True)  
if st.button("Scan Image 😀"):
    if not config.GROQ_API_KEY:
        st.error("Somethings not right. Contact ZingQuark Support at zq1012@gmail.com (GitHub error NOkey)")
    elif not file:
        st.warning("Please Upload A Image!!")  
    else:
        with st.spinner("ZingQuark's AI are Processing your Image..."):
            try:
                data          = analyze_image(file)  
                scene         = data.get("scene_title","AI SCAN Mode")
                object_groups = groups(prepare_objects(data.get("objects", [])), group_size)
                image         = Image.open(BytesIO(file.getvalue()))
                st.session_state.xray_outputs = [
                    hud(image, scene, group, i, len(object_groups))
                    for i, group in enumerate(object_groups, 1)
                ]
                st.success(f"SCAN completed! Created {len(st.session_state.xray_outputs)} scanner image(S).") 
            except Exception as error:
                st.error(f"things dont seem right,, contact zingquark191@gmail.com to assist with your query {error}")     
if st.session_state.xray_outputs:
    st.markdown("## Scanner Results!!")
    for i, output in enumerate(st.session_state.xray_outputs, 1):
        st.image(output, caption=f"ScannerImage {i}", use_container_width=True)    
        st.download_button(
            f"📁 download scanner Image. {i}",
            img_bytes(output),
            f"ai_xray_vision_{i}.png",
            "image/png",
            key=f"download_{i}",

        )                 




# -------------------------------
# Next Steps:
# 1. Add page title, description, and instructions
# 2. Create helper function to analyze the uploaded image with Groq Vision
# 3. Create helper function to convert percentage boxes into pixel coordinates
# 4. Create helper function to clean, filter, and prepare detected objects
# 5. Create helper function to split objects into groups
# 6. Create helper function to load fonts and draw the scanner HUD overlay
# 7. Create helper function to convert final image into downloadable bytes
# 8. Add file uploader and group-size selector
# 9. Preview the uploaded image
# 10. Add button to scan the image and generate grouped scanner outputs
# 11. Display all generated scanner images
# 12. Add download button for each scanner image
# -------------------------------