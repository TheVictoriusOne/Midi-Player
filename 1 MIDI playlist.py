import os
import sys
import json
import time
import subprocess
from random import choice
from pathlib import Path

def cls(): os.system('cls' if os.name == 'nt' else 'clear')
cls()

try: os.mkdir("playlists")
except FileExistsError: pass
except Exception: print("Cannot make a playlists folder.")

def load_playlist():
    while True:
        try:
            playlists = os.listdir("playlists")
            print(f"-- Playlists ({len(playlists)} items) --")
            for i, name in enumerate(playlists): print(name.rsplit(".", 1)[0])
            print("-------------------------")
            playlist_name = input("(Leave empty for new playlist.)\nPlaylist name: ").rsplit(".", 1)[0]
            if playlist_name != "":
                with open("playlists/" + playlist_name + ".json", "r") as f:
                    return json.load(f)
            else:
                return None
        except FileNotFoundError:
            cls()
            print("File not found.")
        except json.JSONDecodeError:
            cls()
            print("File corrupted.")

def save_playlist(playlist):
    cls()
    while True:
        try:
            filename = input("Save playlist as: ").rsplit(".", 1)[0]
            if filename.strip() != "":
                filename = "playlists/" + filename  + ".json"
                with open(filename, "w") as f:
                    json.dump(playlist, f, indent=2)
                    cls()
                    print("Succesfully stored the playlist!")
                    time.sleep(2)
                    return
        except Exception:
            cls()
            print("Couldn't store playlist.")
        
def create_playlist():
    playlist = []
    while len(playlist) == 0:
        midi_name = None
        while midi_name != "":
            cls()
            if midi_name is None:
                pass
            elif Path(midi_name + ".mid").exists():
                playlist.append(midi_name+".mid")
                print(f"Added {midi_name + ".mid"} succesfully.\n")
            else:
                print(f"Unable to find {midi_name + ".mid"}.\n")
            
            print(f"-- Playlist ({len(playlist)} items) --")
            for name in playlist: print(name)
            print( "------------------------\n")
            print("(Leave empty to end.)")
            midi_name = input("MIDI filename: ").rsplit(".", 1)[0]
    return playlist


playlist = load_playlist()
if playlist is None:
    playlist = create_playlist()
    if input("Save playlist? [Y/n]: ").lower() != "n":
        save_playlist(playlist)
        cls()

if len(playlist) < 1:
    print("Playlist appears to somehow be empty.\nQuitting program.")
    exit()

gui_active = input("Allow program to show GUI? [y/N]: ").lower() == "y"
shuffle = input("Shuffle mode? [Y/n]: ").lower() != "n"

version = sys.version_info[0:2]
if version[0] >= 3 and version[1] > 3:
    stdout_val = subprocess.DEVNULL
else:
    stdout_val=open(os.devnull, 'w')
    
stderr_val=subprocess.STDOUT
cls()
try:
    while True:
        prev_midi = set()
        for midi in playlist:
            if shuffle:
                choices = [song for song in playlist if song not in prev_midi]
                midi = choice(choices if choices else playlist)
            cls()
            print(f"Currently playing {midi}")
            subprocess.run([sys.executable, f"0 MIDI Player.py", midi, str(gui_active)], stdout=stdout_val, stderr=stderr_val)
            prev_midi.add(midi)
except KeyboardInterrupt:
    print("Quitting program.")
