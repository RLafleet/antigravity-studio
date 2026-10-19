import subprocess
import sys
import os

target_url = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:48123/assets/monsters/goblin_puppet/puppet_demo.html'
out_path = os.path.abspath(sys.argv[2]) if len(sys.argv) > 2 else os.path.abspath('dungeon_arena_clean.png')
if os.path.exists(out_path):
    try:
        os.remove(out_path)
    except:
        pass

edge_paths = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    "msedge"
]
edge_bin = next((p for p in edge_paths if os.path.exists(p)), "msedge")

cmd = [
    edge_bin,
    '--headless=new',
    '--disable-gpu',
    '--virtual-time-budget=2500',
    f'--screenshot={out_path}',
    '--window-size=750,920',
    target_url
]
res = subprocess.run(cmd, capture_output=True, text=True, shell=False)
print(f"Captured: {out_path}, size={os.path.getsize(out_path) if os.path.exists(out_path) else 'NOT FOUND'}")
