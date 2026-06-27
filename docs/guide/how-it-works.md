# How It Decides Who to Call

When you let Wait and Pounce work for you, the hardest moment is a **busy band**: five, ten, twenty
stations decode at the same instant and only one reply can go out. This page explains, in plain
terms, how the software decides **who to call** — and why it sometimes waits a fraction of a second
before transmitting.

You don't need to read this to use the program, but understanding it makes the
[priority settings](/guide/reply-engine) much easier to tune.

## The 15-second rhythm

FT8 works in **15-second periods** (FT4 is faster). Every period, the radio decodes a batch of
messages all at once. Wait and Pounce treats each batch as a single "round": it looks at everyone
who decoded in **that** period and picks the best station to answer in the next period.

This is the key idea: **it never reacts to one decode in isolation.** It waits for the whole batch,
compares everybody, then commits to one choice.

## Step 1 — Collecting the candidates

As decodes arrive, the software keeps the ones that are actually worth answering — the stations
that match something you want (a wanted callsign, a wanted zone, a needed marathon entity, a new
grid, or someone calling *you*). These go into a short-lived **shortlist** for the current period.

Decodes that match nothing, that are excluded, or that you've already worked (depending on your
[Worked-Before](/guide/worked-before) setting) don't make the shortlist.

Only stations from the **same period** compete with each other. A station heard two periods ago
isn't lumped in with the current batch.

## Step 2 — Ranking the shortlist

Every station on the shortlist is scored. The ranking, from most to least important:

1. **Someone answering you.** If a station is calling *your* callsign, it jumps to the top —
   you're in the middle of a QSO and finishing it always comes first. If it's the very station you
   were already working, it ranks even higher.
2. **Calling CQ.** A station calling CQ is readier to be worked than one already in a QSO with
   someone else, so it gets a small boost.
3. **Your priority order.** Then the software adds a bonus based on *why* the station is wanted —
   wanted callsign, wanted zone, marathon, new grid, or politeness — in the exact order **you** set
   in the [priority settings](/guide/reply-engine). A station matching a higher reason outranks one
   matching a lower reason.

### Breaking a tie

If two stations are still even, the software prefers, in order:

1. the one representing the **more recent** contact opportunity (helps with year-based goals),
2. a station that **uses LoTW** (more likely to confirm your contact),
3. the **stronger** signal (more likely to complete),
4. and finally the one that was **heard first**.

The single highest-ranked station becomes the chosen target.

## Step 3 — The brief pause before transmitting

Here's the part that surprises people: when a new best choice appears, Wait and Pounce arms a
**very short timer (about a fifth of a second)** instead of transmitting immediately.

Why wait at all? Because decodes from the same period don't all land at the exact same millisecond.
If the software fired on the *first* wanted station it saw, it might call a weak duplicate and miss
the rare DX that decoded 100 ms later in the same batch. The tiny pause lets the **entire** batch
arrive so the *final* best choice wins — not whoever happened to decode first.

If a better station shows up during that pause, the timer resets to the new leader. When the pause
ends, the winner is locked in and the reply goes out in the next period.

::: tip Why it sometimes "changes its mind"
On a crowded opening you may see the highlighted target flicker between stations for a split second
before it settles. That's this selection process choosing the best of the batch. It settles before
the next transmit slot — it is not indecision, it's comparison.
:::

## Step 4 — Sticking with the target

Once a station is chosen, the software keeps calling it across the following periods until one of
these happens:

- **the QSO completes** (the station sends its final acknowledgement),
- **time runs out** — your *maximum waiting delay* elapses with no answer, or
- **too many tries** — your *maximum number of attempts* is reached.

When it gives up, the [Watchdog](/guide/watchdog) can set the station aside temporarily so the
software immediately moves on to the next-best target instead of looping on a station that can't
hear you. It also tells the radio to stop transmitting so you're not calling into the void.

## Step 5 — Housekeeping

The shortlist is constantly trimmed: stations older than a couple of minutes drop off so the
comparison always reflects what's being heard **now**, not what was heard long ago.

---

In short: **collect the whole period → rank everyone by your rules → wait a heartbeat for the full
batch → call the single best station → stick with it until it's worked or hopeless.** Everything you
configure in [Choosing Who to Reply To](/guide/reply-engine), [Worked-Before](/guide/worked-before),
[Marathon](/guide/marathon) and [Grid Tracker](/guide/grid-tracker) simply feeds into this ranking.
