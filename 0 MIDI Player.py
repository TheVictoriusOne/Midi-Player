import pygame as pg
from pygame import midi
import time
import base64
import io
import sys

pg.init()
pg.font.init()

midi.init()
out = midi.Output(midi.get_default_output_id()) 

def get_bit(value, index):
    return (value >> index) & 1

def fail(msg):
    print(msg)
    time.sleep(3)
    sys.exit()

# Add a file.
gui_active = True
argv = sys.argv
if len(argv) > 1:
    try:
        if len(argv) > 2: gui_active = sys.argv[2] == "True"
        with open(sys.argv[1], 'rb') as f:
            MIDI = f.read()
    except FileNotFoundError:
        argv = (None)
        
if len(argv) <= 1:
    MIDI = None
    while not MIDI:
        print('Enter the MIDI file name (including .mid!):')
        try:
            with open(input(), 'rb') as f:
                MIDI = f.read()
        except FileNotFoundError:
            print("\nFile not found, please retry.\n")
    

if MIDI[:4].decode() != 'MThd':
    fail('MThd not found, are you sure this is a midi file?')

if MIDI[4:8] != b'\x00\x00\x00\x06':
    fail('MThd size is not 6.')
    
if MIDI[8:10] == b'\x00\x02':
    fail('Format 2 MIDIs are not supported')
    
if MIDI[10:12] == b'\x00\x00':
    fail('MThd claims there are no tracks.')
TrackTotal = int.from_bytes(MIDI[10:12], 'big')

Tempo = 500000
SMPTE_offset = 0
if bool(get_bit(MIDI[12], 7)):
    print('WARNING! SMPTE timecode format detected. \n In the current state which support for it is in, it will most likely not function properly.')
    print('Do you wish to continue? (anY/N)')
    if input() == 'N':
        exit()
        sys.exit()
        
    fps = -int.from_bytes(MIDI[12:13], 'big', signed=True)
    ticks_per_frame = MIDI[13]
    is_smpte = True
    if fps == 29:
        fps = 30000/1001
    else:
        fps = float(fps)
    tick = 1.0 / (fps * ticks_per_frame)
    Divisions = None
else:
    is_smpte = False
    Divisions = int.from_bytes(MIDI[12:14], 'big')
    tick = Tempo / 1000000 / Divisions 

SMPTE_offset = 0

# Find all the track start positions.
Tracks_Found = 0
Track_Pos = []
i = 14
while Tracks_Found != TrackTotal and i < len(MIDI):
    if MIDI[i:i+4].decode() != 'MTrk':
        fail(f'Track {Tracks_Found} has not been found.')
    Track_Pos.append(i)
    Tracks_Found += 1
    i += int.from_bytes(MIDI[i+4:i+8], 'big') + 8

# Parse the whole song!

Music = []
for pos in Track_Pos:
    track_length = int.from_bytes(MIDI[pos+4:pos+8], "big")
    track_end = pos + 8 + track_length
    i = pos + 8
    
    total_delta = 0
    track_events = []
    status = 0
    
    while i < track_end:
        # Retrieve the delta time and add it onto the absolute time.
        delta = 0
        while True:
            byte = MIDI[i]
            delta = (delta << 7) | (byte & 0b01111111)
            i += 1
            if (byte & 0b10000000) == 0:
                break
        total_delta += delta*tick
        if (MIDI[i] & 0b10000000):
            status = MIDI[i]
            i += 1
        event = (status & 0b11110000) >> 4
        event2 = status & 0b00001111 # often times also the channel
        match event:
            case 8 | 9 | 10 | 11 | 14:     # Note OFF | Note ON | Polyphonic Key Pressure | Control Change | Pitch Wheel Change
                track_events.append((event, event2, total_delta, MIDI[i], MIDI[i+1]))
                i += 2
            case 12 | 13:    # Program Change | Channel Pressure
                track_events.append((event, event2, total_delta, MIDI[i]))
                i += 1
            case 15:    # System Events
                match event2:
                    case 15:    # Meta Events
                        meta_type = MIDI[i]
                        i += 1
                        length = 0
                        while True:
                            byte = MIDI[i]
                            length = (length << 7) | (byte & 0b01111111)
                            i += 1
                            if (byte & 0b10000000) == 0:
                                break
                        match meta_type:
                            case 0x00:  # Sequence Number
                                Seq_Num = MIDI[i]
                                track_events.append((event, event2, total_delta, meta_type, Seq_Num))
                            case 0x20:  # Channel Prefix
                                Channel = MIDI[i]
                                track_events.append((event, event2, total_delta, meta_type, Channel))
                            case 0x2F:  # End Of Track
                                track_events.append((event, event2, total_delta, meta_type))
                                break
                            case 0x51:  # Set Tempo
                                Tempo = int.from_bytes(MIDI[i:i+3], 'big')
                                if not (get_bit(MIDI[12], 7)):
                                    tick = Tempo / 1000000 / Divisions
                                track_events.append((event, event2, total_delta, 0x51, Tempo))
                            case 0x54:  # SMPTE Offset
                                hour_byte = MIDI[i]
                                hours = hour_byte & 0x1F
                                fps_map = {0:24, 1:25, 2:30000/1001, 3:30}
                                fps = fps_map.get((hour_byte >> 5) & 0x03, 30)
                                minutes = MIDI[i+1]
                                seconds = MIDI[i+2]
                                frames = MIDI[i+3]
                                fraction = MIDI[i+4]
                                SMPTE_offset = hours * 3600 + minutes * 60 + seconds + frames / fps + fraction / (fps * 100.0)
                                track_events.append((event, event2, total_delta, meta_type, (hours, minutes, seconds, frames, fraction, fps)))
                            case 0x58:
                                Time_Signature = MIDI[i], MIDI[i+1]
                                track_events.append((event, event2, total_delta, meta_type, Time_Signature))
                        i += length
    Music.append(track_events)

# GUI

if gui_active:
    screen = pg.display.set_mode()
    width, height = screen.get_size()
    tile_w = max(1, int(width / 128 / 1.075))
    tile_h = max(1, int(height / 16))
    pg.display.set_caption('Midi Player')
    pg.display.set_icon(pg.image.load(io.BytesIO(base64.b64decode('''iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAMAAABEpIrGAAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAPUExURQAAABYWFp6env///wAAALfXCAkAAAAFdFJOU/////8A+7YOUwAAAAlwSFlzAAAOwgAADsIBFShKgAAAABh0RVh0U29mdHdhcmUAUGFpbnQuTkVUIDUuMS40Et+mgwAAALZlWElmSUkqAAgAAAAFABoBBQABAAAASgAAABsBBQABAAAAUgAAACgBAwABAAAAAgAAADEBAgAQAAAAWgAAAGmHBAABAAAAagAAAAAAAADydgEA6AMAAPJ2AQDoAwAAUGFpbnQuTkVUIDUuMS40AAMAAJAHAAQAAAAwMjMwAaADAAEAAAABAAAABaAEAAEAAACUAAAAAAAAAAIAAQACAAQAAABSOTgAAgAHAAQAAAAwMTAwAAAAALAIjE6kK4+AAAAATElEQVQ4T+3OSwoAIAgEUFPvf+by0y5tkQRBQwNKbyHwJiUAsihocR4CWRQgjUlL8ny2/YNigF4Bc7bdgXysew3gOCiogiwC8pwC5g69lweRRNtytwAAAABJRU5ErkJggg=='''))))
    my_font = pg.font.SysFont('cascadiamonoregular', int(1/36 * height))

    fade = pg.Surface((width, height), pg.SRCALPHA)
    fade.fill((0,0,0,18))

    channel_colors = (
        (255,   0,   0),
        (255, 165,   0),
        (255, 255,   0),
        (  0, 128,   0),
        (  0, 255,   0),
        (  0, 128, 128),
        (  0, 255, 255),
        (  0,   0, 255),
        (  0,   0, 128),
        (128,   0, 128),
        (255,   0, 255),
        (128,   0,   0),
        (128, 128,   0),
        (192, 192, 192),
        (128, 128, 128),
        (255, 255, 255)
        )

def render_GUI():
    screen.blit(fade, (0,0))
    for note, channel in active_notes:
        coords = (int(note * tile_w + width*0.075), int(channel * tile_h))

        color = channel_colors[channel]
        
        rect = pg.Rect(coords, (tile_w, tile_h))
        pg.draw.rect(screen, color, rect)
    
    for y in range(16):
        pg.draw.line(screen, (50, 50, 50), (0, y*tile_h), (width, y*tile_h))
        screen.blit(my_font.render(f'CH {y}', True, channel_colors[y]), (tile_w, y*tile_h + tile_h * 0.25))
    pg.draw.line(screen, (50, 50, 50), (0, 16*tile_h-1), (width, 16*tile_h-1))
    pg.draw.line(screen, (200, 200, 200), (width*0.075, 0), (width*0.075, height))
    
    pg.display.flip()

# Playback the MIDI

clock = pg.Clock()

start_time = time.perf_counter_ns()

all_events = []
for track in Music:
    all_events.extend(track)


all_events.sort(key=lambda ev: ev[2])


active_notes = []
for events in all_events:
    time_test = time.perf_counter_ns()
    if pg.event.get(pg.QUIT): exit()
    time_test = time.perf_counter_ns() - time_test
    if time_test > 100000000:
        start_time += time_test
    
    
    while (time.perf_counter_ns() - start_time) < events[2] * 1000000000:
        clock.tick(120)
        if gui_active: render_GUI()
        if round(time.perf_counter_ns() * 0.0000001) & 120 == 4:
            if pg.event.get(pg.QUIT): exit()
        
    match events[0]:
        case 8:     # Note Off
            out.note_off(note=events[3], velocity=events[4], channel=events[1])
            if (events[3], events[1]) in active_notes:
                active_notes.remove((events[3], events[1]))
        case 9:     # Note On
            if events[4] == 0:
                out.note_off(note=events[3], velocity=events[4], channel=events[1])
                if (events[3], events[1]) in active_notes:
                    active_notes.remove((events[3], events[1]))
            else:
                out.note_on(note=events[3], velocity=events[4], channel=events[1])
                active_notes.append((events[3], events[1]))
        case 10:     # Polyphonic Key Pressure
            #print("Polyphonic Key Pressure")
            out.write_short(0xA0 | events[1], 1, events[3], events[4])
        case 11:     # Control Change
            out.write_short(0xB0 | events[1], events[3], events[4])
        case 12:     # Program Change
            #print("Program Change")
            out.set_instrument(events[3], channel=events[1])
        case 13:     # Channel Pressure
            #print("Channel Pressure")
            out.write_short(0xD0 | events[1], events[3])
        case 14:     # Pitch Wheel Change
            #print("Pitch Wheel Change")
            out.write_short(0xE0 | events[1], events[3], events[4])
        case 15:
            pass
