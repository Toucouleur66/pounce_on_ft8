---
layout: home

hero:
  name: "Wait and Pounce"
  text: "FT8 / FT4 DX Pounce Assistant"
  tagline: Automatically reply to the DX you want, on the bands you choose, while WSJT-X or JTDX does the heavy lifting.
  image:
    src: /logo.png
    alt: Wait and Pounce logo
  actions:
    - theme: brand
      text: Get Started
      link: /guide/introduction
    - theme: alt
      text: How It Works
      link: /guide/how-it-works
    - theme: alt
      text: All Settings
      link: /reference/settings

features:
  - title: 🎯 Smart Pouncing
    details: Watches every WSJT-X / JTDX decode and replies to your wanted callsigns, CQ zones, new grids and DX-Marathon entities — automatically, with a configurable priority order.
  - title: 📡 Works with WSJT-X & JTDX
    details: Listens on the UDP server, forwards packets, and keys your radio by sending Reply packets. No modification of WSJT-X or JTDX required.
  - title: 🗂️ Logbook-Aware
    details: Parses your ADIF logbook to know what you've already worked. Worked-Before logic, per-year tracking, and a built-in logbook analyzer.
  - title: 🏆 DX Marathon & Grid Tracking
    details: Hunt every DXCC entity once per year, or chase new Maidenhead grids regardless of band, with an interactive grid map.
  - title: ☁️ LoTW & Club Log
    details: Auto-upload contacts to Logbook of The World (via TQSL) and Club Log in real time, and download confirmations back into your log.
  - title: 🔗 Multi-Instance Sync
    details: Run a Master and one or more Slave instances across rigs; wanted lists and reply state stay in sync automatically.
---

## What is Wait and Pounce?

**Wait and Pounce** is a companion application for the popular weak-signal digital modes
software **WSJT-X** and **JTDX**. Where WSJT-X handles the FT8/FT4 protocol, decoding and
the radio, Wait and Pounce adds an intelligent **automatic-reply ("pounce") engine** on top:
you tell it *who* and *what* you want to work, and it watches the decode stream and replies on
your behalf the instant a target appears.

It is written in **Python 3 / PyQt6**, runs on **Windows and macOS**, and talks to WSJT-X / JTDX
purely over the standard **UDP network protocol** (default port `2237`).

::: tip New here?
Start with the [Introduction](/guide/introduction), then read
[How It Works](/guide/how-it-works) to understand the pounce engine before configuring anything.
:::
