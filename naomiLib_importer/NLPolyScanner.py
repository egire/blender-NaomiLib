#! /usr/bin/env python3

"""
Created 16.09.2020 18:34 CEST

@author zocker_160
@comment script for analysing NaomiLib 3D files

this is an implementation of the NaomiLib documentation created by Vincent
without that, this implementation would be impossible, all credits go to him
"""

import os
import sys
import struct
import re

from io import BytesIO

folder = "C:\\mods\\doa2\\out\\BAS00\\"

magic_naomilib = [
    b'\x01\x00\x00\x00\x01\x00\x00\x00',  # Super index , always true
    b'\x00\x00\x00\x00\x01\x00\x00\x00',  # Pure beta , always true
    b'\x01\x00\x00\x00\x02\x00\x00\x00',  # Super index , skip 1st light source
    b'\x00\x00\x00\x00\x02\x00\x00\x00',  # Pure beta , skip 1st light source
    b'\x01\x00\x00\x00\x03\x00\x00\x00',  # Super index , always true , skip 1st light source
    b'\x00\x00\x00\x00\x03\x00\x00\x00',  # Pure beta , always true , skip 1st light source
    b'\x01\x00\x00\x00\x05\x00\x00\x00',  # Super index , always true , Environment mapping
    b'\x00\x00\x00\x00\x05\x00\x00\x00',  # Pure Beta , always true , Environment mapping
    b'\x01\x00\x00\x00\x07\x00\x00\x00',  # Super index , always true , Environment mapping, skip 1st light source
    b'\x00\x00\x00\x00\x07\x00\x00\x00',  # Pure Beta , always true , Environment mapping, skip 1st light source
    b'\x01\x00\x00\x00\x11\x00\x00\x00',  # Super index , always true , Bump mapping
    b'\x00\x00\x00\x00\x11\x00\x00\x00',  # Pure Beta , always true , Bump mapping
    b'\x01\x00\x00\x00\x19\x00\x00\x00',  # Super index , always true , Bump mapping, palette texture
    b'\x00\x00\x00\x00\x19\x00\x00\x00',  # Pure Beta , always true , Bump mapping, palette texture
    b'\x01\x00\x00\x00\x15\x00\x00\x00',  # Super index , always true , Environment mapping, Bump mapping
    b'\x00\x00\x00\x00\x15\x00\x00\x00',  # Pure Beta , always true , Environment mapping, Bump mapping
]


pattern = b'[\x01-\xFF][\x00-\x01]\x00\x00[\x01-\xFF]\x00\x00\x00'

model_mesh_byte_offset = 104
polyheader_size = 8
model_mesh_byte_footer_size = 8

# create list
typeList = []

# open folder and read all files
for file in os.listdir(folder):
    if not file.endswith(".bin"):
        continue
    
    filename = file
    
    file = folder + file

    with open(file, "rb") as nlfile:

        if not (nlfile.read(8) in magic_naomilib):
            print(f"ERROR: {filename} is not a NaomiLib file!")

        nlfile.seek(0x68) # 104 bytes (model header and mesh struct)

        # get current position in file to end of file
        file_data = nlfile.read()

        # scan to end of file finding the byte pattern
        # FF OO/01 OO OO FF OO OO OO
        # use regex to find byte pattern
        # pattern must align with 0x00 or 0x08 position
        # and must start finding at 0x68 position

        # Use re to search for the pattern
        matches = list(re.finditer(pattern, file_data))

        # Check and print results
        if matches:
            for match in matches:
                match_pos = match.start() + model_mesh_byte_offset
                # Check if the match aligns with 00 or 08 position
                polyHeader = match.group()[:4].hex(' ', 1)
                polySize = int.from_bytes(match.group()[4:], "little")
                if match_pos % 8 == 0:
                    print(f"File {filename}. Polygon found at position: {match_pos} - Header: {polyHeader} Size: {polySize}")

                    #add match to list

                    if match_pos > 104:
                        typeList[-1][4] = match_pos-(typeList[-1][1]+polyheader_size)

                    typeList.append([filename, match_pos, polyHeader, polySize, 0])
            nlfile.seek(0, os.SEEK_END)
            typeList[-1][4] = nlfile.tell() - model_mesh_byte_footer_size - typeList[-1][1] - polyheader_size
        else:
            print("Pattern not found.")
#output list to csv file
with open("polygons.csv", "w") as f:
    f.write("Filename,Start,PolyHeader,PolySize,Bytes\n")
    for item in typeList:
        f.write(f"{item[0]},{item[1]},{item[2]},{item[3]},{item[4]}\n")
