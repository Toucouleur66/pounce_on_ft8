# DX-Pounce for FT8 QSOs (Wait, search, and pounce)

## About

This repository contains the source code used to handle FT8 QSO automation for `WSJT-X` or `JTDX`. This type of automation is not recommended but remains usefull to avoid to spend your entire life waiting in front of your screen because listening to audio alone does not allow you to decode anything in `FT8` (or `SuperFox`). This did not prevent me from having to make many iterations to this program to make it work. Basically, it will read your `ALL.TXT` log files, check for some sequences, and will Enable or Disable TX on your `JTDX` or `WSJT-X` instance. It does support `SuperFox Mode (S/F)`.

Please check the `TODO`.

Think about a donation to let me find time to improve this program. I hope you will enjoy using this program, and you will get fun to search and pounce for DX. 

Works For Windows Platform only for now.

## How to use it

- pip install -r requirements.txt
- Get a correct version working for Super/Fox mode with `WSJT-X` or `JTDX` and installed
- Make sure to update `wait_and_pounce.py` around line 710
```
# Update window tile
wsjt_window_title = "WSJT-X   v2.7.1-devel   by K1JT et al."
jtdx_window_title = "JTDX - FT5000  by HF community                                         v2.2.160-rc7 , derivative work based on WSJT-X by K1JT"
```
- Launch GUI using command line with Python. Ex: `python3 pounce_gui.pyw`

## Donate with PayPal

[![Donate](https://img.shields.io/badge/Donate-PayPal-green.svg)](https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=R4HK9ZTUPYHSL)

## Version

- `1.1` Handle Wildcard (use "`*`" as Wildcard)
- `1.0` Show status on `GUI`
- `0.9` Handle multiple calls
- `0.8` Set mode to start on `Normal`or `Fox/Hound` or `SuperFox`
- `0.7` Change for odd or even `JTDX`
- `0.6` Force `your_call` and `call_selected` to be uppercase
- `0.5` Handle `Super/Fox` Mode from `JTDX v2.2.160-rc7`
- `0.4` Use latest modified `*ALL.TXT` files `<== You are here`
- `0.3` Allow to set your call instead of editing configuration `wait_and_pounce.
- `0.2` Handle frequency change (frequency_hopping) and close once finished
- `0.1` Initial version, reading logs

## Known bugs

## `WSJT-X` (S/F)
- [x] Issue while handle output sequence
- [ ] Logging QSO remains an issue due to variable size of the log window

## `JTDX` (Regular Mode, F/H and S/F)
- [x] When focus after reading for the first time log file, doesn't Enable TX immediately
- [x] When `JTDX` does not have a callsign set at `DX Call`, can't set any new callsign and generate message
- [ ] Sometime, `replace_input_field_content` method can't set number for a callsign

## TODO
- [ ] Let end user set his own filepath
- [ ] Set mode Hound or Super Fox to `JTDX`
- [ ] Add clean button for output Widget
- [ ] Allow use of Wildcard for Wanted callsigns
- [ ] Add Widget to GUI when focus on callsign
- [ ] Add scrollbar to output Widget
- [ ] Find clear QRG for TXing
- [ ] Let end user set his own `JTDX` and `WSJT-X` window title and position
- [ ] Make binary for `Windows`
- [ ] Check `wsjtx_log.adi` to get confirmation of awaited QSO
- [ ] Add internationalization `I18N` and localization `L10N`
- [ ] Use `Packet UDP` instead of reading log files
- [x] Fix `Log Analysis Count`
- [x] Disable Run button unless user set `your_callsign` and `wanted_callsigns`
- [x] Set `JTDX` to `SHound` Mode
- [x] Change for odd or even `JTDX`
- [x] Output within a `TXT` log file
- [x] Show status on __GUI__
- [x] Handle multiple calls
- [x] Handle latest known ALL log files
- [x] Setting caller
- [x] GUI
- [x] Band hoping 
- [x] Wait for sequence, if found in the last 10 minutes then call otherwise return monitoring
- [x] Frequency update and support with JTDX
- [x] Compare log time `UTC` with local machine time

## Make binary for Windows

```pyinstaller --windowed --onefile --debug all C:\Users\YourDirectory]\pounce_on_ft8\pounce_gui.pyw```

## Donate with PayPal

[![Donate](https://img.shields.io/badge/Donate-PayPal-green.svg)](https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=R4HK9ZTUPYHSL)

## Need to read UDP packets coming from either WSJT-X or JTDX
- https://github.com/bmo/py-wsjtx
- https://github.com/takgr/JTDX-controller/blob/main/call_alert.py
- https://github.com/rstagers/WSJT-X
- https://github.com/bmo/py-wsjtx
- https://github.com/SA0TAY/potassium