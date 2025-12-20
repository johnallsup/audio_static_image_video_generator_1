# Audio Static Image Vidoe Generator 1
Efficiently convert audio and static image into a video by concatenating a seed loop.

These are two simple wrapper scripts using ffmpeg and Pillow to do the heavy lifting.
They were generated using Gemini.
One is a command line utility (with slight adaptions) and a Qt app using PySide6.

This was kind of an experiment in vibe coding, with something that nobody's 
life depends upon. I just asked Gemini for a few things, and the result is what
you find here.

Its purpose is to scratch an itch that some of us have when we want to 
quickly upload an audio file to Youtube. Creating a whole video in a video editor
takes time, even for a static image, and rendering also takes time,
much longer than is necessary using this method.

## Temporary Files
Since naturally it is necessary to be able to write to the target directory,
we create temporary files there, and then clean them up afterwards.

## Dependencies
The script requires a Python 3 installation (3.10 is sufficient) with PySide6
and Pillow installed.

## Windows
If the system Python has PySide6 and Pillow installed, then 
`SimpleStaticVideoGenerator.py`
can be run from the explorer.

Quite possibly this could be packaged as a self-contained `.exe`
but that hasn't be done here (yet).

## Icons
The icons are just the result of asking Gemini for one once the working
program was finished.
