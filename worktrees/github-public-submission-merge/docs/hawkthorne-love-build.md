# Building Windows executables for LÖVE projects (Hawkthorne reference)

This project style does **not** compile in the traditional "build an executable from source" sense for local development.

For local iteration, `./make.ps1 run` runs/tests the game, but it does **not** produce release executables.

## How the Windows `.exe` is produced

1. Build `build/hawkthorne.love` from `src/` (zip bundle).
2. Download the LÖVE runtime (`love.exe`).
3. Concatenate runtime + bundle:

   ```batch
   copy /b bin\win64\love.exe + build\hawkthorne.love build\win64\hawkthorne.exe

4. Copy required runtime files (e.g., `SDL2.dll`, `OpenAL32.dll`, and others from the LÖVE release) alongside your new executable. For a complete list, see the [LÖVE Game Distribution guide](https://love2d.org/wiki/Game_Distribution). Then, package them into release zips (`hawkthorne-win64.zip` / `hawkthorne-win32.zip`).

## Release-oriented targets

Use Make targets when you need distributable artifacts:

- `make build/hawkthorne-win64.zip`
- `make binaries` (build all platforms available on host)

## Upstream references

- Makefile: <https://raw.githubusercontent.com/hawkthorne/hawkthorne-journey/master/Makefile>
- PowerShell helper: <https://raw.githubusercontent.com/hawkthorne/hawkthorne-journey/master/make.ps1>
- README: <https://raw.githubusercontent.com/hawkthorne/hawkthorne-journey/master/README.md>
