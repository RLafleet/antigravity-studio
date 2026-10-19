import os
import sys
from PIL import Image
import numpy as np

def slice_spritesheet(image_path, num_frames=6, output_dir="assets/monsters/goblin_idle"):
    os.makedirs(output_dir, exist_ok=True)
    img = Image.open(image_path).convert("RGBA")
    width, height = img.size
    arr = np.array(img)

    # Detect character vs chroma-key background (#FF0000)
    is_bg = (arr[:, :, 0] > 150) & (arr[:, :, 1] < 80) & (arr[:, :, 2] < 80)
    is_char = ~is_bg
    col_has_char = np.any(is_char, axis=0)

    # Find contiguous character column segments
    segments = []
    in_seg = False
    start = 0
    for x, has in enumerate(col_has_char):
        if has and not in_seg:
            in_seg = True
            start = x
        elif not has and in_seg:
            in_seg = False
            if x - start > 20: # ignore minor noise
                segments.append((start, x))
    if in_seg and len(col_has_char) - start > 20:
        segments.append((start, len(col_has_char)))

    print(f"Detected {len(segments)} character segments in {image_path} (expected {num_frames})")

    # Smart midpoint cutting between characters
    if len(segments) == num_frames:
        cut_points = [0]
        for i in range(num_frames - 1):
            mid = (segments[i][1] + segments[i+1][0]) // 2
            cut_points.append(mid)
        cut_points.append(width)
    else:
        frame_width = width // num_frames
        cut_points = [i * frame_width for i in range(num_frames)] + [width]

    max_w = max(cut_points[i+1] - cut_points[i] for i in range(num_frames))

    frames = []
    for i in range(num_frames):
        box = (cut_points[i], 0, cut_points[i+1], height)
        frame = img.crop(box)

        # Chroma key: convert red pixels to alpha 0
        f_arr = np.array(frame)
        red_mask = (f_arr[:, :, 0] > 150) & (f_arr[:, :, 1] < 90) & (f_arr[:, :, 2] < 90)
        f_arr[red_mask, 3] = 0
        cleaned = Image.fromarray(f_arr, "RGBA")

        # Center in uniform canvas while preserving ground line
        canvas = Image.new("RGBA", (max_w, height), (0, 0, 0, 0))
        offset_x = (max_w - (cut_points[i+1] - cut_points[i])) // 2
        canvas.paste(cleaned, (offset_x, 0))

        frame_file = os.path.join(output_dir, f"frame_{i}.png")
        canvas.save(frame_file, "PNG")
        frames.append(f"frame_{i}.png")
        print(f"Saved: {frame_file} ({max_w}x{height})")

    # Generate interactive HTML preview
    preview_html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Goblin Idle Animation Preview</title>
  <style>
    body {{
      background: #0d1117;
      color: #e6edf3;
      font-family: -apple-system, sans-serif;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
      margin: 0;
    }}
    .container {{
      background: #161b22;
      border: 1px solid #30363d;
      border-radius: 16px;
      padding: 24px;
      text-align: center;
      box-shadow: 0 8px 24px rgba(0,0,0,0.5);
    }}
    .stage {{
      width: {max_w}px;
      height: {height // 2}px;
      margin: 20px auto;
      background: radial-gradient(circle, #21262d 0%, #0d1117 70%);
      border: 2px dashed #388bfd;
      border-radius: 12px;
      display: flex;
      align-items: flex-end;
      justify-content: center;
      position: relative;
      overflow: hidden;
    }}
    .ground-line {{
      position: absolute;
      bottom: 20px;
      left: 0;
      right: 0;
      height: 2px;
      background: rgba(56, 139, 253, 0.4);
    }}
    #goblin-sprite {{
      max-width: 100%;
      max-height: 100%;
      image-rendering: auto;
    }}
    .controls {{
      margin-top: 16px;
      display: flex;
      align-items: center;
      gap: 12px;
      justify-content: center;
    }}
    button {{
      background: #238636;
      color: white;
      border: none;
      padding: 8px 16px;
      border-radius: 8px;
      cursor: pointer;
      font-weight: bold;
    }}
    button:hover {{ background: #2ea043; }}
    input[type=range] {{ width: 140px; }}
  </style>
</head>
<body>
  <div class="container">
    <h2>👹 Тест анимации дыхания Гоблина (Idle Animation)</h2>
    <p style="color: #8b949e; font-size: 13px;">6 кадров, нарезанных из спрайт-листа с альфа-каналом</p>
    
    <div class="stage">
      <div class="ground-line"></div>
      <img id="goblin-sprite" src="frame_0.png" />
    </div>

    <div class="controls">
      <button id="btn-toggle" onclick="togglePlay()">⏸ Пауза</button>
      <label>Скорость: <span id="fps-label">6</span> FPS</label>
      <input type="range" min="1" max="15" value="6" oninput="changeFps(this.value)">
    </div>
    <div style="margin-top: 10px; font-size: 12px; color: #8b949e;">Кадр: <span id="frame-num">0</span> / {num_frames - 1}</div>
  </div>

  <script>
    const frames = {frames};
    let current = 0;
    let fps = 6;
    let playing = true;
    let interval = null;

    function nextFrame() {{
      current = (current + 1) % frames.length;
      document.getElementById('goblin-sprite').src = frames[current];
      document.getElementById('frame-num').textContent = current;
    }}

    function start() {{
      if (interval) clearInterval(interval);
      interval = setInterval(nextFrame, 1000 / fps);
    }}

    function togglePlay() {{
      playing = !playing;
      const btn = document.getElementById('btn-toggle');
      if (playing) {{
        btn.textContent = "⏸ Пауза";
        start();
      }} else {{
        btn.textContent = "▶️ Старт";
        clearInterval(interval);
      }}
    }}

    function changeFps(val) {{
      fps = parseInt(val);
      document.getElementById('fps-label').textContent = fps;
      if (playing) start();
    }}

    start();
  </script>
</body>
</html>
"""
    preview_file = os.path.join(output_dir, "preview.html")
    with open(preview_file, "w", encoding="utf-8") as f:
        f.write(preview_html)
    print(f"Preview generated: {preview_file}")
    return preview_file

if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else "assets/monsters/goblin_raw_sheet.png"
    slice_spritesheet(src)
