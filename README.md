# DX-Pounce for FT8 QSOs

## About

This repository contains the source code used to handle FT8 QSO automation for `WSJT/JTDX`

## Donate with PayPal

[![Donate](https://img.shields.io/badge/Donate-PayPal-green.svg)](https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=R4HK9ZTUPYHSL)

## Version

- [0.4] Use latest modified `*ALL.TXT` files
- [0.3] Allow to set your call instead of editing configuration `wait_and_pounce.py`
- [0.2] Handle frequency change (frequency_hopping) and close once finished
- [0.1] Initial version, reading logs

## Known bugs

## WSJT-X (S/F)
- [x] Issue while handle output sequence
- [ ] Logging QSO remains an issue due to variable size of the log window

## JTDX (Regular Mode & F/H)
- [x] When JTDX does not have a callsign set at DX Call, can't set any new callsign and generate message
- [ ] Sometime, `replace_input_field_content` method can't set number for a callsign, issue was found while monitoring 3V8SS

## TODO

- [ ] Output within a TXT log file
- [ ] Show status on GUI
- [ ] Handle multiple call
- [ ] Let end user set his own Windows title and position
- [ ] Check `wsjtx_log.adi` to get confirmation of awaited QSO
- [ ] Change for odd or even (JTDX)
- [ ] Add internationalization (I18N) and localization (L10N) 
- [ ] Use `Packet UDP`
- [x] Handle latest known ALL log files
- [x] Setting caller
- [x] GUI
- [x] Band hoping 
- [x] Wait for sequence, if found in the last 10 minutes then call otherwise return monitoring
- [x] Frequency update and support with JTDX
- [x] Compare log time `UTC` with local machine time

## Donate with PayPal

[![Donate](https://img.shields.io/badge/Donate-PayPal-green.svg)](https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=R4HK9ZTUPYHSL)

## Need to read UDP packets coming frm either WSJT-X or JTDX
- https://github.com/rstagers/WSJT-X
- https://github.com/bmo/py-wsjtx
- https://github.com/SA0TAY/potassium