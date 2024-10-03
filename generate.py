import pymunk
from pymunk import Vec2d
from wand.image import Image
from wand.drawing import Drawing
from wand.color import Color
import subprocess
import os
from pydub import AudioSegment
from pydub.generators import Sine
import numpy as np

# Configuration
FRAME_WIDTH = 600
FRAME_HEIGHT = 600
BACKGROUND_COLOR = 'white'
OBJECT_COLOR = 'blue'
FLOOR_COLOR = 'black'
FRAME_RATE = 60
DURATION = 5  # seconds
TOTAL_FRAMES = FRAME_RATE * DURATION
FRAME_FOLDER = 'frames'
SOUND_FOLDER = 'sounds'
AUDIO_OUTPUT = 'audio.wav'
VIDEO_ONLY = 'video_only.mp4'
FINAL_VIDEO = 'simulation_with_audio.mp4'

# Ensure directories exist
os.makedirs(FRAME_FOLDER, exist_ok=True)
os.makedirs(SOUND_FOLDER, exist_ok=True)

# Generate or load collision sound
collision_sound_path = os.path.join(SOUND_FOLDER, 'collision.wav')
if not os.path.exists(collision_sound_path):
    def generate_collision_sound(output_path, duration_ms=100, frequency=440):
        sine_wave = Sine(frequency).to_audio_segment(duration=duration_ms)
        collision_sound = sine_wave.fade_out(50)
        collision_sound.export(output_path, format="wav")
    
    generate_collision_sound(collision_sound_path)

# Initialize PyMunk
space = pymunk.Space()
space.gravity = (0, 900)

# Create static floor
floor = pymunk.Segment(space.static_body, (50, 550), (550, 550), 5)
floor.elasticity = 0.8
space.add(floor)

# Create dynamic circle
mass = 1
radius = 25
moment = pymunk.moment_for_circle(mass, 0, radius)
body = pymunk.Body(mass, moment)
body.position = (300, 100)
shape = pymunk.Circle(body, radius)
shape.elasticity = 0.8
space.add(body, shape)

# Collision event tracking
collision_times = []

def collision_handler(arbiter, space, data):
    """
    Callback function to handle collision events.
    Logs the simulation time when a collision occurs.
    """
    collision_times.append(space.current_time)
    return True

# Set up collision handler
handler = space.add_default_collision_handler()
handler.post_solve = collision_handler

# Rendering function
def draw_frame(space, filename):
    with Image(width=FRAME_WIDTH, height=FRAME_HEIGHT, background=Color(BACKGROUND_COLOR)) as img:
        with Drawing() as draw:
            # Draw floor
            floor_start = floor.a
            floor_end = floor.b
            draw.stroke_color = Color(FLOOR_COLOR)
            draw.stroke_width = 5
            draw.line([floor_start.x, floor_start.y], [floor_end.x, floor_end.y])

            # Draw circle
            circle_pos = body.position
            draw.fill_color = Color(OBJECT_COLOR)
            draw.circle((circle_pos.x, circle_pos.y), (circle_pos.x + radius, circle_pos.y))
            
            draw(img)
        img.save(filename=filename)

# Simulation loop
space.current_time = 0.0  # Initialize simulation time
for frame in range(TOTAL_FRAMES):
    # Step the physics
    dt = 1 / FRAME_RATE
    space.step(dt)
    space.current_time += dt
    
    # Render the current frame
    frame_filename = os.path.join(FRAME_FOLDER, f'frame_{frame:04d}.png')
    draw_frame(space, frame_filename)
    
    if frame % FRAME_RATE == 0:
        print(f'Rendered frame {frame}/{TOTAL_FRAMES}')

print("All frames rendered.")

# Generate the audio track
def generate_audio_track(collision_times, collision_sound_path, total_duration, output_path, frame_rate):
    """
    Generates an audio track with collision sounds placed at specified times.
    
    :param collision_times: List of times (in seconds) when collisions occur.
    :param collision_sound_path: Path to the collision sound effect.
    :param total_duration: Total duration of the audio track in seconds.
    :param output_path: Path to save the generated audio.
    :param frame_rate: Frame rate of the video.
    """
    # Create a silent audio segment
    audio = AudioSegment.silent(duration=total_duration * 1000)  # duration in milliseconds
    
    # Load collision sound
    collision_sound = AudioSegment.from_wav(collision_sound_path)
    
    # Overlay collision sounds at the specified times
    for collision_time in collision_times:
        collision_ms = int(collision_time * 1000)
        if collision_ms < len(audio):
            audio = audio.overlay(collision_sound, position=collision_ms)
    
    # Export the final audio track
    audio.export(output_path, format="wav")

generate_audio_track(
    collision_times=collision_times,
    collision_sound_path=collision_sound_path,
    total_duration=DURATION,
    output_path=AUDIO_OUTPUT,
    frame_rate=FRAME_RATE
)

print("Audio track generated.")

# Compile video with FFmpeg (without audio)
ffmpeg_video_command = [
    'ffmpeg',
    '-y',  # Overwrite output file if it exists
    '-framerate', str(FRAME_RATE),
    '-i', os.path.join(FRAME_FOLDER, 'frame_%04d.png'),
    '-c:v', 'libx264',
    '-pix_fmt', 'yuv420p',
    VIDEO_ONLY
]

print("Compiling video with FFmpeg...")
subprocess.run(ffmpeg_video_command, check=True)
print(f"Video saved as {VIDEO_ONLY}")

# Combine video and audio using FFmpeg
ffmpeg_combine_command = [
    'ffmpeg',
    '-y',  # Overwrite output file if it exists
    '-i', VIDEO_ONLY,
    '-i', AUDIO_OUTPUT,
    '-c:v', 'copy',
    '-c:a', 'aac',
    '-strict', 'experimental',
    FINAL_VIDEO
]

print("Combining video and audio with FFmpeg...")
subprocess.run(ffmpeg_combine_command, check=True)
print(f"Final video saved as {FINAL_VIDEO}")
