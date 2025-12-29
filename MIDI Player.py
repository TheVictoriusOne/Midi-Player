import pygame as pg
from pygame import midi
import time
import sys

pg.init()
pg.font.init()
my_font = pg.font.SysFont('cascadiamonoregular', 30)

midi.init()
out = midi.Output(midi.get_default_output_id()) 

def get_bit(value, index):
    return (value >> index) & 1

def fail(msg):
    print(msg)
    sys.exit()

# Check if the file is correct.

print('Enter the MIDI file name (including .mid!):')
with open(input(), 'rb') as f:
    MIDI = f.read()

if MIDI[:4].decode() != 'MThd':
    fail('MThd not found, are you sure this is a midi file?')

if MIDI[4:8] != b'\x00\x00\x00\x06':
    fail('MThd size is not 6.')
    
if MIDI[8:10] == b'\x00\x02':
    fail('Format 2 MIDIs are not supported')
    
if MIDI[10:12] == b'\x00\x00':
    fail('MThd claims there are no tracks.')
TrackTotal = int.from_bytes(MIDI[10:12], 'big')
    
if get_bit(MIDI[12], 7):
    fail('SMPTE Timecode is not supported by this MIDI player.')
Divisions = int.from_bytes(MIDI[12:14], 'big')

# Calculate the standard Tick
Tempo = 500000
tick = Tempo / 1000000 / Divisions

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
            case 8:     # Note OFF
                Note = MIDI[i]
                Velocity = MIDI[i+1]
                track_events.append((event, event2, total_delta, Note, Velocity))
                i += 2
            case 9:     # Note ON
                Note = MIDI[i]
                Velocity = MIDI[i+1]
                track_events.append((event, event2, total_delta, Note, Velocity))
                i += 2
            case 10:    # Polyphonic Key Pressure
                Note = MIDI[i]
                Pressure = MIDI[i+1]
                track_events.append((event, event2, total_delta, Note, Pressure))
                i += 2
            case 11:    # Control Change
                Control = MIDI[i]
                Value = MIDI[i+1]
                track_events.append((event, event2, total_delta, Control, Value))
                i += 2
            case 12:    # Program Change
                Program = MIDI[i]
                track_events.append((event, event2, total_delta, Program))
                i += 1
            case 13:    # Channel Pressure
                Pressure = MIDI[i]
                track_events.append((event, event2, total_delta, Pressure))
                i += 1
            case 14:    # Pitch Wheel Change
                lsb = MIDI[i]
                msb = MIDI[i+1]
                track_events.append((event, event2, total_delta, lsb, msb))
                i += 2
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
                                tick = Tempo / 1000000 / Divisions
                            case 0x54:  # SMPTE Offset
                                fail('Received SMPTE Offset Meta Event, while it is not supported.')
                            case 0x58:
                                Time_Signature = MIDI[i], MIDI[i+1]
                                track_events.append((event, event2, total_delta, meta_type, Time_Signature))
                i += length
    Music.append(track_events)

# GUI

width, height = (1800, 960)
tile_w = max(1, int(width / 128 / 1.075))
tile_h = max(1, int(height / 16))
screen = pg.display.set_mode((width, height))
pg.display.set_caption('Midi Player')
pg.display.set_icon(pg.image.load('icon.png'))

def render_GUI():
    screen.fill((0, 0, 0))
    for y in range(16):
        pg.draw.line(screen, (50, 50, 50), (0, y*tile_h), (width, y*tile_h))
        screen.blit(my_font.render(f'CH {y}', True, (255,255,255)), (tile_w, y*tile_h + tile_h * 0.25))
    pg.draw.line(screen, (200, 200, 200), (width*0.075, 0), (width*0.075, height))
    for note, channel in active_notes:
        coords = (int(note * tile_w + width*0.075), int(channel * tile_h))
        r = int((note * 2) % 256)
        g = 0
        b = int((channel * 32 + 20) % 256)
        color = (r, g, b)
        rect = pg.Rect(coords, (tile_w, tile_h))
        pg.draw.rect(screen, color, rect)
    pg.display.flip()

# Playback the MIDI

start_time = time.time_ns()

all_events = []
for track in Music:
    all_events.extend(track)


all_events.sort(key=lambda ev: ev[2])

active_notes = []
for events in all_events:
    for event in pg.event.get():
        if event.type == pg.QUIT:
            exit()
    render_GUI()
    while (time.time_ns() - start_time) / 1000000 < events[2] * 1000:
        pass
    match events[0]:
        case 8:     # Note Off
            print("Note Off")
            out.note_off(note=events[3], velocity=events[4], channel=events[1])
            if (events[3], events[1]) in active_notes:
                active_notes.remove((events[3], events[1]))
        case 9:     # Note On
            if events[4] == 0:
                print("Note Off")
                out.note_off(note=events[3], velocity=events[4], channel=events[1])
                active_notes.remove((events[3], events[1]))
            else:
                print("Note On")
                out.note_on(note=events[3], velocity=events[4], channel=events[1])
                active_notes.append((events[3], events[1]))
        case 10:     # Polyphonic Key Pressure
            print("Polyphonic Key Pressure")
            out.write_short(0xA0 | events[1], 1, events[3], events[4])
        case 11:     # Control Change
            match events[3]:
                case 0x07:      # Channel Volume
                    print("Channel Volume")
                    out.write_short(0xB0 | events[1], 0x07, events[4])
                case 0x0A:      # Pan
                    print("Pan Channel")
                    out.write_short(0xB0 + events[1], 0x0A, events[4])
                case 0x0B:      # Expression
                    print("Expression")
                    out.write_short(0xB0 + events[1], 0x0B, events[4])
                case 0x40:      # Sustain
                    print("Sustain")
                    pass
        case 12:     # Program Change
            print("Program Change")
            out.set_instrument(events[3], channel=events[1])
        case 13:     # Channel Pressure
            print("Channel Pressure")
            out.write_short(0xD0 | events[1], events[3])
        case 14:     # Pitch Wheel Change
            print("Pitch Wheel Change")
            out.write_short(0xE0 | events[1], events[3], events[4])
        case 15:
            pass
    