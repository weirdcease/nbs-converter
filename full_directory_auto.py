import os

import automatic

for filename in os.listdir("songs"):
    filename_min = filename.lower().replace('(', '').replace(')', '').replace(' ', '_')
    if os.path.isfile(os.path.join("formatted", filename_min)):
        print(f"{filename}: skipped, already done")
        continue
    else:
        print(f"{filename}: converting...")
        file_path = os.path.join("songs", filename)
        formatted_path = automatic.format_song(file_path)
        automatic.gen_schematic(formatted_path)