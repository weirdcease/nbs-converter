import pynbs
import os
import sys
import shutil
import numpy
import mcschematic

import nbs_format_song as form
import nbs_generate_schematic as gen

MC_SCHEMS_DIR = "/home/cas/.local/share/multimc/instances/1.20.1/.minecraft/config/worldedit/schematics"

base_dir = os.path.dirname(__file__)

def format_song(song_path: str, do_compress: bool = False): # version of main from nbs_format_song.py that doesn't use input
    try:
        song = pynbs.read(song_path)
        song_name = os.path.split(song_path)[1].rsplit(".", 1)[0]
  
    except:
        sys.exit(f'Error: could not find "{song_path}"')

    og_song_length = song.header.song_length
    if og_song_length > form.MAX_SONG_LENGTH and do_compress:
        setting_compress = 1
    else:
        setting_compress = 0

    for note in song.notes:
        if note.key < form.INSTRUMENT_RANGE[0] or note.key > form.INSTRUMENT_RANGE[1]:
            print('Your song contains notes that are outside the normal range. They will be transposed to be playable.')
  
    if len(song.instruments) > 0:
        print('Your song contains custom instruments. All notes using custom instruments will be removed.')
  
    new_song = pynbs.new_file()
    new_song.header = song.header
    new_song.layers = song.layers
    new_song.header.tempo = 5

    has_max_chord_violation = 0

    for tick, chord in song:
        new_tick = tick
        if setting_compress:
            new_tick = tick // 2
        if new_tick > form.MAX_SONG_LENGTH:
            print('Notice: Your song was too long, so some had to be cut off the end.')
            break
        if (tick % 2 != 0 and setting_compress == 0) or (tick %2 == 0):
            chord = form.removeCustomNotes(chord)
            chord = form.fixIllegalNotes(chord)
            [chord, chordViolation] = form.removeChordViolations(chord)
            if chordViolation == 1:
                has_max_chord_violation = 1
            for note in chord:
                note.tick = new_tick
                note.panning = 0
                note.pitch = 0
                new_song.notes.append(note)
    
    if has_max_chord_violation:
        print('Notice: Your song contained chords that were larger than allowed. Some notes were removed from these chords.')

    balls = song_name.lower().replace('(', '').replace(')', '').replace(' ', '_')
    new_file_name = os.path.join(base_dir, "formatted", balls+".nbs")
    print(new_file_name)
    new_song.save(new_file_name)
    print('Your formatted song was saved under "'+new_file_name+'"')
    return new_file_name

def gen_schematic(song_path: str):
    try:
        song = pynbs.read(song_path)
        song_name = os.path.split(song_path)[1].rsplit(".", 1)[0]
    except:
        sys.exit('Error: could not find "' + song_path + '"')
    
    gen.verifyFormat(song)

    last_chest_fill = (song.header.song_length + 1) % 27
    song_length_adjusted = song.header.song_length + 1
    if last_chest_fill >= 1 and last_chest_fill < gen.CHEST_MIN_FILL:
        song_length_adjusted += gen.CHEST_MIN_FILL - last_chest_fill

    all_chest_contents = {}
    empty_chest = numpy.full(song_length_adjusted, -1)
    for instrument in gen.INSTRUMENTS:
        all_chest_contents[instrument] = []
        for _ in range(gen.CHORD_MAX_SIZES[instrument]):
            all_chest_contents[instrument].append([empty_chest.copy(), empty_chest.copy()])

    key_modifier = gen.INSTRUMENT_RANGE[0]
    current_indices = {}
    for tick, chord in song:
        for instrument in gen.INSTRUMENTS:
            current_indices[instrument] = [0, 0]
        
        for note in chord:
            instrument = gen.INSTRUMENTS[note.instrument]
            adjusted_key = note.key - key_modifier
            octave = 0 if adjusted_key <= 11 else 1
            all_chest_contents[instrument][current_indices[instrument][octave]][octave][tick] = adjusted_key
            current_indices[instrument][octave] += 1
    
    minimal_chest_contents = gen.removeEmptyChests(all_chest_contents)

    # turn minimalChestContents into a schematic
    schem = mcschematic.MCSchematic()
    offset = 0
    print('Generating Schematic...')
    for instrument, contents in minimal_chest_contents.items():
        currentModule = 1
        for module in contents:
            lower_chest_1 = ''
            upper_chest_1 = ''
            lower_chest_2 = ''
            upper_chest_2 = ''
            lower_shulker = ''
            upper_shulker = ''
            current_shulker = 1
            lower_octave_empty = len(module[0]) == 0
            upper_octave_empty = len(module[1]) == 0
            for current_tick in range(song_length_adjusted):
                current_slot = current_tick % 27
                if lower_octave_empty == 0:
                    lower_shulker += gen.newDisc(current_slot, module[0][current_tick]) + ','
                if upper_octave_empty == 0:
                    upper_shulker += gen.newDisc(current_slot, module[1][current_tick]) + ','
                # if we are on the last slot of a shulker box, or the song has ended
                if (current_tick + 1) % 27 == 0 or current_tick == song_length_adjusted - 1:
                    # turn the shulker contents into actual shulker
                    if lower_octave_empty == 0:
                        lower_shulker = gen.createShulker(current_shulker, lower_shulker)
                    if upper_octave_empty == 0:
                        upper_shulker = gen.createShulker(current_shulker, upper_shulker)
                    # if the current shulker should go in the first chests
                    if current_shulker <= 27:
                        if lower_octave_empty == 0:
                            lower_chest_1 += lower_shulker + ','
                        if upper_octave_empty == 0:
                            upper_chest_1 += upper_shulker + ','
                    else:
                        if lower_octave_empty == 0:
                            lower_chest_2 += lower_shulker + ','
                        if upper_octave_empty == 0:
                            upper_chest_2 += upper_shulker + ','
                    # reset the shulkers and increment the current shulker
                    lower_shulker = ''
                    upper_shulker = ''
                    current_shulker += 1
        
            if lower_octave_empty == 0:
                lower_chest_1 = gen.createChest('right', lower_chest_1)
                lower_chest_2 = gen.createChest('left', lower_chest_2)
                schem.setBlock((offset, 0, -1), lower_chest_1)
                schem.setBlock((offset + 1, 0, -1), lower_chest_2)
                schem.setBlock((offset, 0, 0), gen.createSign(instrument, currentModule, 0))
            else:
                schem.setBlock((offset, 0, -1), "minecraft:air")
                schem.setBlock((offset + 1, 0, -1), "minecraft:air")
                schem.setBlock((offset, 0, 0), "minecraft:air")
            
            if upper_octave_empty == 0:
                upper_chest_1 = gen.createChest('right', upper_chest_1)
                upper_chest_2 = gen.createChest('left', upper_chest_2)
                schem.setBlock((offset, 1, -1), upper_chest_1)
                schem.setBlock((offset + 1, 1, -1), upper_chest_2)
                schem.setBlock((offset, 1, 0), gen.createSign(instrument, currentModule, 1))
            else:
                schem.setBlock((offset, 1, -1), "minecraft:air")
                schem.setBlock((offset + 1, 1, -1), "minecraft:air")
                schem.setBlock((offset, 1, 0), "minecraft:air")
            
            currentModule += 1
            offset += 2
    
    save_name = song_name.lower().replace('(', '').replace(')', '').replace(' ', '_')
    save_path = os.path.join(base_dir, "schematics", save_name)
    print(f"Saving under {save_path}")
    schem.save('', save_path, mcschematic.Version.JE_1_20)
    print('Your schematic was successfully generated and saved under "schematics/' + save_name + '.schem"')

    if os.path.isdir(MC_SCHEMS_DIR):
        shutil.copyfile(os.path.join(base_dir, "schematics", save_name+".schem"), os.path.join(MC_SCHEMS_DIR, save_name+".schem"))
        print("Copied into Minecraft schematics directory.")

def main():
    for directory in ["songs", "formatted", "schematics"]:
        dir_path = os.path.join(base_dir, directory)
        if not os.path.isdir(dir_path):
            os.mkdir(dir_path)

    if len(sys.argv) < 2:
        print("You must supply a path to an nbs file")
        sys.exit(1)

    nbs_path = sys.argv[1]
    formatted_path = format_song(nbs_path)
    gen_schematic(formatted_path)

if __name__ == "__main__":
    main()