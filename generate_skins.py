import os
import numpy as np
from PIL import Image, ImageFilter

def create_skins():
    src_path = 'assets/models/monster_texture.jpg'
    img = Image.open(src_path).convert('RGB')
    orig_np = np.array(img, dtype=np.float32) / 255.0
    
    r = orig_np[:, :, 0]
    g = orig_np[:, :, 1]
    b = orig_np[:, :, 2]
    
    # Perceptual luminance
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    
    # High-pass filter to extract fine vein/crack detail
    blurred = img.filter(ImageFilter.GaussianBlur(radius=6))
    blur_np = np.array(blurred, dtype=np.float32) / 255.0
    blur_lum = 0.299 * blur_np[:, :, 0] + 0.587 * blur_np[:, :, 1] + 0.114 * blur_np[:, :, 2]
    
    fine_detail = np.clip((lum - blur_lum) * 2.5, -1.0, 1.0)
    
    # -------------------------------------------------------------
    # 1. LAVA / MAGMA SKIN
    # -------------------------------------------------------------
    # Detect cracks: original red highlights + fine ridges + high luminance
    red_accent = np.clip((r - (g + b) * 0.5) * 3.0, 0, 1.0)
    crack_mask = np.clip(red_accent * 1.5 + (fine_detail > 0.15) * 0.8 + (lum > 0.48) * 0.9, 0, 1.0)
    
    # Smooth crack mask for realistic heat bleed
    heat_glow = np.clip(crack_mask * 1.2, 0, 1.0)
    hot_core = np.clip((crack_mask - 0.4) * 2.2, 0, 1.0)
    
    # Volcanic obsidian base
    lava_diff = np.zeros_like(orig_np)
    # Basalt rock
    lava_diff[:, :, 0] = lum * 0.14 + 0.04
    lava_diff[:, :, 1] = lum * 0.11 + 0.03
    lava_diff[:, :, 2] = lum * 0.11 + 0.03
    
    # Add magma flame
    # Outer crust glow (crimson red)
    lava_diff[:, :, 0] = lava_diff[:, :, 0] * (1.0 - heat_glow) + (0.95 * heat_glow)
    lava_diff[:, :, 1] = lava_diff[:, :, 1] * (1.0 - heat_glow) + (0.28 * heat_glow)
    lava_diff[:, :, 2] = lava_diff[:, :, 2] * (1.0 - heat_glow) + (0.02 * heat_glow)
    
    # Inner hot core (bright yellow-white)
    lava_diff[:, :, 0] = np.clip(lava_diff[:, :, 0] + hot_core * 0.35, 0, 1.0)
    lava_diff[:, :, 1] = np.clip(lava_diff[:, :, 1] + hot_core * 0.65, 0, 1.0)
    lava_diff[:, :, 2] = np.clip(lava_diff[:, :, 2] + hot_core * 0.25, 0, 1.0)
    
    # Lava Emissive: only glowing cracks
    lava_emissive = np.zeros_like(orig_np)
    lava_emissive[:, :, 0] = np.clip(heat_glow * 1.2 + hot_core * 0.2, 0, 1.0)
    lava_emissive[:, :, 1] = np.clip(heat_glow * 0.45 + hot_core * 0.6, 0, 1.0)
    lava_emissive[:, :, 2] = np.clip(hot_core * 0.2, 0, 1.0)
    
    # -------------------------------------------------------------
    # 2. TOXIC / ACID GOBLIN SKIN
    # -------------------------------------------------------------
    toxic_mask = np.clip(crack_mask * 1.1 + (fine_detail > 0.1) * 0.6, 0, 1.0)
    toxic_core = np.clip((toxic_mask - 0.45) * 2.0, 0, 1.0)
    
    toxic_diff = np.zeros_like(orig_np)
    # Dark reptilian swamp green
    toxic_diff[:, :, 0] = lum * 0.10 + 0.03
    toxic_diff[:, :, 1] = lum * 0.28 + 0.08
    toxic_diff[:, :, 2] = lum * 0.08 + 0.02
    
    # Acid glow (neon green / yellow)
    toxic_diff[:, :, 0] = toxic_diff[:, :, 0] * (1.0 - toxic_mask) + (0.35 * toxic_mask)
    toxic_diff[:, :, 1] = toxic_diff[:, :, 1] * (1.0 - toxic_mask) + (0.95 * toxic_mask)
    toxic_diff[:, :, 2] = toxic_diff[:, :, 2] * (1.0 - toxic_mask) + (0.15 * toxic_mask)
    
    # Toxic Emissive
    toxic_emissive = np.zeros_like(orig_np)
    toxic_emissive[:, :, 0] = np.clip(toxic_mask * 0.25 + toxic_core * 0.3, 0, 1.0)
    toxic_emissive[:, :, 1] = np.clip(toxic_mask * 0.95 + toxic_core * 0.2, 0, 1.0)
    toxic_emissive[:, :, 2] = np.clip(toxic_mask * 0.15, 0, 1.0)
    
    # -------------------------------------------------------------
    # 3. FROST / GLACIER TITAN SKIN
    # -------------------------------------------------------------
    frost_mask = np.clip(crack_mask * 1.1 + (fine_detail > 0.1) * 0.7, 0, 1.0)
    frost_core = np.clip((frost_mask - 0.4) * 2.0, 0, 1.0)
    
    frost_diff = np.zeros_like(orig_np)
    # Cold deep navy frozen rock
    frost_diff[:, :, 0] = lum * 0.10 + 0.03
    frost_diff[:, :, 1] = lum * 0.16 + 0.06
    frost_diff[:, :, 2] = lum * 0.32 + 0.14
    
    # Crystalline cyan-white ice
    frost_diff[:, :, 0] = frost_diff[:, :, 0] * (1.0 - frost_mask) + (0.45 * frost_mask)
    frost_diff[:, :, 1] = frost_diff[:, :, 1] * (1.0 - frost_mask) + (0.85 * frost_mask)
    frost_diff[:, :, 2] = frost_diff[:, :, 2] * (1.0 - frost_mask) + (1.00 * frost_mask)
    
    # Bright frosted core
    frost_diff[:, :, 0] = np.clip(frost_diff[:, :, 0] + frost_core * 0.45, 0, 1.0)
    frost_diff[:, :, 1] = np.clip(frost_diff[:, :, 1] + frost_core * 0.35, 0, 1.0)
    frost_diff[:, :, 2] = np.clip(frost_diff[:, :, 2] + frost_core * 0.10, 0, 1.0)
    
    # Frost Emissive
    frost_emissive = np.zeros_like(orig_np)
    frost_emissive[:, :, 0] = np.clip(frost_mask * 0.15 + frost_core * 0.4, 0, 1.0)
    frost_emissive[:, :, 1] = np.clip(frost_mask * 0.65 + frost_core * 0.3, 0, 1.0)
    frost_emissive[:, :, 2] = np.clip(frost_mask * 0.95 + frost_core * 0.1, 0, 1.0)

    # Save all texture sets
    skins = [
        ('assets/models/skin_lava_diff.jpg', lava_diff, 'assets/models/skin_lava_emis.jpg', lava_emissive),
        ('assets/models/skin_toxic_diff.jpg', toxic_diff, 'assets/models/skin_toxic_emis.jpg', toxic_emissive),
        ('assets/models/skin_frost_diff.jpg', frost_diff, 'assets/models/skin_frost_emis.jpg', frost_emissive),
    ]
    
    for diff_path, diff_arr, emis_path, emis_arr in skins:
        Image.fromarray((diff_arr * 255).astype(np.uint8)).save(diff_path, quality=92)
        Image.fromarray((emis_arr * 255).astype(np.uint8)).save(emis_path, quality=90)
        print(f'Saved: {diff_path} and {emis_path}')

if __name__ == '__main__':
    create_skins()
