# DXCC Program

The **DXCC** award is for working 100+ "entities" (countries). Wait and Pounce's **DXCC Program**
mode turns the assistant into an entity-hunter that chases the DXCC entities you still need — **all
time**, regardless of year (unlike [Marathon](/guide/marathon), which resets each calendar year).

## What it does

When DXCC Program is enabled for a band, a decoded station becomes a reply candidate if its **DXCC
entity** has not yet been worked on that band (based on your loaded [logbook](/guide/adif)). When a
station is chosen on this basis, Wait and Pounce replies to it just like any other target.

## Configuring it

In **Settings → DXCC Program**:

- **Per-band buttons** — choose which bands the entity check applies to. An entity is "needed" if you
  haven't worked it *on that band*, all-time.
- **Keep replying to an entity until it is confirmed (QSL)** — by default a single contact marks an
  entity as worked. Turn this on to keep calling stations from the same entity until you actually
  have a **confirmation**, which is useful when chasing award credit.
- **Unlimited** — chase any DXCC entity not yet worked on **any** band (band-agnostic).

## DXCC Program vs Marathon

Both hunt DXCC entities, but with different rules:

| | DXCC Program | [Marathon](/guide/marathon) |
|---|---|---|
| Time window | **All time** | **Current year** only |
| "Worked" resets | Never | Every 1 January |
| Confirmation option | Can require a QSL | Contact only |

You can run both at once; where each ranks against your other targets is set in
[Choosing Who to Reply To](/guide/reply-engine).
