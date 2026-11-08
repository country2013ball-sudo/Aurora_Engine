import asyncio
import base64
from io import BytesIO
import math
import flet as ft
from PIL import Image, ImageDraw

class RenderEngine:
    """Core engine responsible for generating and caching graphical frames."""
    def __init__(self, width: int = 360, height: int = 360):
        self.width = width
        self.height = height
        self.frames: list[str] = []

    async def generate_sequence(self, frame_count: int = 30, frequency: float = 2.0, progress_callback=None) -> list[str]:
        """Generates a sequence of procedural graphic frames asynchronously."""
        self.frames.clear()
        center_x, center_y = self.width / 2, self.height / 2
        max_radius = min(self.width, self.height) * 0.35

        for i in range(frame_count):
            img = Image.new("RGBA", (self.width, self.height), color=(18, 18, 24, 255))
            draw = ImageDraw.Draw(img)
            
            t = i / frame_count
            angle_offset = t * 2 * math.pi * frequency
            
            num_nodes = 8
            for n in range(num_nodes):
                node_phase = (n / num_nodes) * 2 * math.pi + angle_offset
                r = max_radius * (0.6 + 0.4 * math.sin(node_phase * 2))
                px = center_x + r * math.cos(node_phase)
                py = center_y + r * math.sin(node_phase)
                
                color_alpha = int(120 + 100 * math.sin(node_phase))
                draw.line([(center_x, center_y), (px, py)], fill=(0, 220, 255, color_alpha), width=2)
                
                node_size = 12 + 6 * math.sin(node_phase * 3)
                draw.ellipse(
                    [(px - node_size, py - node_size), (px + node_size, py + node_size)],
                    fill=(255, 64, 128, 230), outline=(255, 255, 255, 200), width=2
                )
                
            draw.ellipse([(center_x - 18, center_y - 18), (center_x + 18, center_y + 18)], fill=(0, 255, 180, 255))
            
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            b64_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
            self.frames.append(b64_str)
            
            if progress_callback:
                progress_callback(i + 1, frame_count)
            
            await asyncio.sleep(0.001)
            
        return self.frames

async def main(page: ft.Page):
    page.title = "Frame Render Studio"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 16
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.scroll = ft.ScrollMode.ADAPTIVE
    
    engine = RenderEngine(width=360, height=360)
    is_playing = False
    current_frame_idx = 0
    fps = 24

    viewport_image = ft.Image(src_base64="", width=340, height=340, fit=ft.ImageFit.CONTAIN, border_radius=ft.border_radius.all(12))
    viewport_container = ft.Container(
        content=viewport_image, width=350, height=350, bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
        border_radius=16, border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT), alignment=ft.alignment.center
    )
    
    frame_label = ft.Text("Frame: 0 / 0", size=14, weight=ft.FontWeight.W_500)
    progress_bar = ft.ProgressBar(value=0.0, visible=False, width=340)
    timeline_slider = ft.Slider(min=0, max=0, divisions=1, value=0, width=340, disabled=True)
    
    play_pause_button = ft.IconButton(icon=ft.Icons.PLAY_ARROW_ROUNDED, icon_size=32, disabled=True)
    frames_input = ft.Slider(min=10, max=120, divisions=11, value=30, label="{value} frames")
    frequency_input = ft.Slider(min=0.5, max=5.0, divisions=9, value=1.5, label="{value}x freq")
    fps_slider = ft.Slider(min=10, max=60, divisions=5, value=24, label="{value} FPS")

    def update_frame(idx: int):
        nonlocal current_frame_idx
        if not engine.frames: return
        current_frame_idx = idx % len(engine.frames)
        viewport_image.src_base64 = engine.frames[current_frame_idx]
        timeline_slider.value = current_frame_idx
        frame_label.value = f"Frame: {current_frame_idx + 1} / {len(engine.frames)}"
        page.update()

    async def play_loop():
        nonlocal is_playing, current_frame_idx
        while is_playing and engine.frames:
            current_frame_idx = (current_frame_idx + 1) % len(engine.frames)
            update_frame(current_frame_idx)
            await asyncio.sleep(1.0 / fps)

    async def toggle_play(e):
        nonlocal is_playing
        if not engine.frames: return
        is_playing = not is_playing
        play_pause_button.icon = ft.Icons.PAUSE_ROUNDED if is_playing else ft.Icons.PLAY_ARROW_ROUNDED
        page.update()
        if is_playing:
            await play_loop()

    def on_seek(e):
        nonlocal is_playing
        if is_playing:
            is_playing = False
            play_pause_button.icon = ft.Icons.PLAY_ARROW_ROUNDED
        update_frame(int(e.control.value))

    def on_fps_change(e):
        nonlocal fps
        fps = int(e.control.value)

    fps_slider.on_change = on_fps_change
    play_pause_button.on_click = toggle_play
    timeline_slider.on_change = on_seek

    async def generate_frames(e):
        nonlocal is_playing
        is_playing = False
        play_pause_button.icon = ft.Icons.PLAY_ARROW_ROUNDED
        play_pause_button.disabled = True
        timeline_slider.disabled = True
        progress_bar.visible = True
        progress_bar.value = None 
        page.update()
        
        total_frames = int(frames_input.value)
        freq = float(frequency_input.value)

        def on_progress(done, total):
            progress_bar.value = done / total
            frame_label.value = f"Rendering: {done}/{total}"
            page.update()

        await engine.generate_sequence(frame_count=total_frames, frequency=freq, progress_callback=on_progress)

        progress_bar.visible = False
        timeline_slider.disabled = False
        timeline_slider.max = total_frames - 1
        timeline_slider.divisions = max(1, total_frames - 1)
        play_pause_button.disabled = False
        update_frame(0)

    render_button = ft.FilledButton(
        content=ft.Row([ft.Icon(ft.Icons.AUTO_AWESOME), ft.Text("Generate Sequence", size=16)], alignment=ft.MainAxisAlignment.CENTER),
        width=340, height=48, on_click=generate_frames,
    )

    page.add(
        ft.Text("Canvas Render Viewport", size=20, weight=ft.FontWeight.BOLD),
        viewport_container,
        frame_label,
        progress_bar,
        timeline_slider,
        ft.Row([
            ft.IconButton(icon=ft.Icons.SKIP_PREVIOUS_ROUNDED, on_click=lambda _: update_frame(current_frame_idx - 1)),
            play_pause_button,
            ft.IconButton(icon=ft.Icons.SKIP_NEXT_ROUNDED, on_click=lambda _: update_frame(current_frame_idx + 1)),
        ], alignment=ft.MainAxisAlignment.CENTER),
        ft.Divider(height=24),
        ft.Text("Render Parameters", size=16, weight=ft.FontWeight.W_600),
        ft.Text("Frame Count:", size=12, color=ft.Colors.GREY_400),
        frames_input,
        ft.Text("Frequency / Speed:", size=12, color=ft.Colors.GREY_400),
        frequency_input,
        ft.Text("Playback FPS:", size=12, color=ft.Colors.GREY_400),
        fps_slider,
        render_button,
    )

if __name__ == "__main__":
    ft.app(target=main)
