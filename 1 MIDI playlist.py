import os
import sys
import json
import time
import subprocess
from random import shuffle
from pathlib import Path

# Short function to wipe the terminal screen.
def cls(): os.system('cls' if os.name == 'nt' else 'clear')
cls()

# Folder must exist to store potential playlists in.
Path("playlists").mkdir(exist_ok=True)

# Hand the user all items inside of the playlists folder
def load_playlist():
    while True:
        try:
            playlists = [item for item in os.listdir("playlists") if item.endswith(".json")]
            print(f"-- Playlists ({len(playlists)} item{"s" if len(playlists) != 1 else ""}) --")
            for i, item in enumerate(playlists, 1): print(f"{i} - {item[:-5]}")
            print("-------------------------")
            playlist_item = input("(Leave empty for new playlist.)\nPlaylist name: ").strip()
            if playlist_item == "": return None

            if not playlist_item.lower().endswith(".json"):
                playlist_item += ".json"

            if playlist_item in playlists:
                with open("playlists/" + playlist_item, "r") as f:
                    playlist = json.load(f)
                    if isinstance(playlist, list) and len(playlist) > 0 and all(isinstance(item, str) for item in playlist):
                        return playlist
                    else:
                        cls()
                        print("Invalid playlist format.")
            else:
                cls()
                print("Playlist not found.")
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
            filename = input("Save playlist as: ").strip()
            filename = Path(filename).name
            if filename:
                if not filename.lower().endswith(".json"):
                    filename += ".json"

                with open("playlists/" + filename, "w") as f:
                    json.dump(playlist, f, indent=2)
                    cls()
                    print("Succesfully stored the playlist!")
                    time.sleep(2)
                    return
            
        except OSError as e:
            cls()
            print("Couldn't store playlist: ", e)
        
def create_playlist():
    playlist = []
    while len(playlist) == 0:
        midi_name = None
        while midi_name != "":
            cls()
            if midi_name is None:
                pass
            elif Path(midi_name + ".mid").is_file():
                playlist.append(midi_name+".mid")
                print(f"Added {midi_name + ".mid"} succesfully.\n")
            else:
                print(f"Unable to find {midi_name + ".mid"}.\n")
            
            print(f"-- Playlist ({len(playlist)} items) --")
            for name in playlist: print(name)
            print( "------------------------\n")
            print("(Leave empty to end.)")
            midi_name = input("MIDI filename: ").strip()
            if midi_name.lower().endswith(".mid"):
                midi_name = midi_name[:-4]
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
shuffling = input("Shuffle mode? [Y/n]: ").lower() != "n"

stdout_val = subprocess.DEVNULL
stderr_val=subprocess.STDOUT
cls()
try:
    while True:
        shuffled = playlist.copy()
        if shuffling: shuffle(shuffled)
            
        for midi in shuffled:
            cls()
            print(f"Currently playing {midi}")
            subprocess.run([sys.executable, f"0 MIDI Player.py", midi, str(gui_active)], stdout=stdout_val, stderr=stderr_val)
except KeyboardInterrupt:
    print("Quitting program.")
