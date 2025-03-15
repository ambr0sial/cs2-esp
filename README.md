# cs2 simple esp

a simple and clean external memory-reading only esp for counter-strike 2

## features

- enemy esp (green color by default)
  - box esp
  - health bar
  - name esp
  - distance esp
  - weapon esp
  - skeleton esp
  - line esp
- teammate esp (blue color by default)
  - single toggle to apply all active enemy esp features to teammates
- color customization
  - change enemy and teammate colors with built-in color picker
  - 9 different color options for both teams
- sleek and minimal ui
- customizable settings

## details

- **type**: external (memory reading only)
- **safety**: relatively safe as it only reads memory and doesn't write to it

## usage

1. download the latest release to the right of the page (releases section)
2. open `cs2-simple-esp.exe` (cs2 should be opened)
3. that's it!! you can press the insert key to toggle the menu

## how it works

this is an external esp cheat that works by:

1. reading game memory to get player positions
2. dynamically fetching offsets from github
3. drawing esp features on top of the game using an overlay
4. not writing to memory at any point (read-only)

## disclaimer

this project is for educational purposes only. using cheats in online games may result in your account being banned. use at your own risk
