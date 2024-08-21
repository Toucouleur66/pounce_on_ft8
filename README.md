# DX-Pounce for FT8 QSOs

## About

This repository contains the source code used to handle FT8 QSO automation for WSJT/JTDX

## Version

v0.3    - Allow to set user call instead of editing configuration waint_and_pounce.py
v0.2    - Handle frequency change (frequency_hopping) and close once finished
v0.1    - Initial version, reading logs

## Known bugs

- [x] Issue while handle output sequence from WSJT-X
- [x] When JTDX does not have a call yet, can't set anything
- [ ] Logging QSO remains a issue due to variable size of the log window
- [ ] Problem found while trying to set some callsign for example issue was found with 3V8SS

## TODO

- [ ] Output log file 
- [ ] Output from GUI
- [ ] Handle multiple call
- [ ] Check wsjtx_log.adi
- [ ] Change for odd or even
- [ ] Use Packet UDP
- [x] Setting caller
- [x] GUI
- [x] Band hoping 
- [x] Wait for sequence, if found in the last 10 minutes then call otherwise return monitoring
- [x] Frequency update and support with JTDX
- [x] Compare log time (UTC) with local machine time

## Need to read UDP packets coming frm either WSJT-X or JTDX
- https://github.com/rstagers/WSJT-X
- https://github.com/bmo/py-wsjtx
- https://github.com/SA0TAY/potassium