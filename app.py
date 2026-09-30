import os, random, uuid
import mysql.connector
import requests
from flask import Flask, jsonify, render_template, request, send_from_directory
from urllib.parse import quote

app = Flask(__name__)

DB = dict(host="localhost", user="root", password="your_password",
          database="image_generator")

OUT_DIR = os.path.join(app.static_folder, "generated")
os.makedirs(OUT_DIR, exist_ok=True)

STYLES = {
    "None": "",
    "Realistic photo": ", ultra realistic photograph, sharp focus, natural light",
    "Digital art": ", digital art, highly detailed, vibrant colors",
    "Anime": ", anime style illustration, clean lines",
    "3D render": ", 3D render, soft studio lighting, octane render",
    "Oil painting": ", oil painting on canvas, visible brush strokes",
}
SIZES = {"Square": (1024, 1024), "Landscape": (1280, 720), "Portrait": (720, 1280)}


def run(sql, args=(), write=False):
    con = mysql.connector.connect(**DB)
    cur = con.cursor(dictionary=True)
    cur.execute(sql, args)
    if write:
        con.commit()
        result = cur.lastrowid
    else:
        result = cur.fetchall()
    cur.close()
    con.close()
    return result


@app.route("/")
def home():
    history = run("SELECT id, prompt, filename FROM images ORDER BY id DESC LIMIT 12")
    return render_template("index.html", history=history,
                           styles=list(STYLES), sizes=list(SIZES))


@app.route("/api/generate", methods=["POST"])
def generate():
    d = request.get_json()
    prompt = (d.get("prompt") or "").strip()
    style = d.get("style") if d.get("style") in STYLES else "None"
    width, height = SIZES.get(d.get("size"), SIZES["Square"])

    if len(prompt) < 3:
        return jsonify(ok=False, msg="Write a few words describing the image first."), 400
    if len(prompt) > 300:
        return jsonify(ok=False, msg="Keep the prompt under 300 characters."), 400

    full_prompt = prompt + STYLES[style]
    url = "https://image.pollinations.ai/prompt/" + quote(full_prompt, safe="")
    params = {"width": width, "height": height, "model": "flux",
              "seed": random.randint(1, 999999), "nologo": "true"}
    try:
        r = requests.get(url, params=params, timeout=120)
    except requests.RequestException:
        return jsonify(ok=False, msg="Could not reach the image service. Check your internet."), 502

    if r.status_code == 429:
        return jsonify(ok=False, msg="Too many requests. Wait 15 seconds and try again."), 429
    if r.status_code != 200 or not r.headers.get("content-type", "").startswith("image"):
        return jsonify(ok=False, msg=f"Image service error ({r.status_code}). Try again."), 502

    filename = uuid.uuid4().hex + ".jpg"
    with open(os.path.join(OUT_DIR, filename), "wb") as f:
        f.write(r.content)
    new_id = run("INSERT INTO images (prompt, style, filename) VALUES (%s,%s,%s)",
                 (prompt, style, filename), write=True)
    return jsonify(ok=True, id=new_id, prompt=prompt,
                   url=f"/static/generated/{filename}", download=f"/download/{new_id}")


@app.route("/download/<int:image_id>")
def download(image_id):
    rows = run("SELECT filename FROM images WHERE id=%s", (image_id,))
    if not rows:
        return "Image not found", 404
    return send_from_directory(OUT_DIR, rows[0]["filename"], as_attachment=True,
                               download_name=f"ai-image-{image_id}.jpg")


if __name__ == "__main__":
    app.run(debug=True)
