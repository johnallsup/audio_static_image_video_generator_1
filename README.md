# Audio Static Image Video Generator 1
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

This is very much a quick hack to scratch an itch, and not a professionally polished application. In part it was an exercise in taking something I had a `bash` script for, and ask Gemini to write a better version in Python with an optional GUI.

## Temporary Files
Since naturally it is necessary to be able to write to the target directory,
we create temporary files there, and then clean them up afterwards.

## Dependencies
The script requires a Python 3 installation (3.10 is sufficient) with PySide6
and Pillow installed.

There needs to be `ffmpeg` and `ffprobe` installed, and in the `PATH`.
If necessary, the hack from the Macos section can be employed:
edit the Python script to tell it where `ffmpeg` and `ffprobe` are.

## Macos
In the `qt_macos` directory is a simple `setup.py` and `build.sh`.
Provided the necessaries are installed (`py2app` for example),
then running 
```
. ./build.sh
``` 
will generate a `.app` in the `dist` folder.

There is a quick and dirty hack for finding `ffmpeg` and
`ffprobe`. It uses `shutil.which` and if this fails, adds
some directories like `/usr/local/bin`, `/opt/local/bin`,
and `$HOME/bin` to the `PATH` and tries again. If necessary
you'll need to edit the Python script to add paths as necessary
(that is, if you know where `ffmpeg` and `ffprobe` are,
include those paths in the list).

Look for the bit here (around line 30)
```
    # 2. Update PATH: Add common macOS/Linux locations
    extra_paths = [
        "/usr/local/bin",
        "/opt/local/bin",
        os.path.expanduser("~/bin")
    ]
```
and add whatever path is needed.

Then the `.app` can be dragged into your `/Applications` and
it works.

## Tk Version
The Qt version doesn't work on Macos before 11.0. Thus there is a second
Tkinter based version, which is a completely separate AI-produced
script that does roughly the same thing.

The `tk_macos` directory contains a `setup.py` to build this into an `.app`.

## Windows
If the system Python has PySide6 and Pillow installed, then 
`SimpleStaticVideoGenerator.py`
can be run from the explorer.

Quite possibly this could be packaged as a self-contained `.exe`
but that hasn't be done here (yet).

## Icons
The icons are just the result of asking Gemini for one once the working
program was finished.
