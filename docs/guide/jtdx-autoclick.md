# JTDX Auto-Click

JTDX (unlike WSJT-X) pops up a **"Log QSO" confirmation window** after each contact that must be
dismissed before the next QSO can proceed. Wait and Pounce's **Automate tasks** feature can click
that prompt for you so unattended pouncing isn't interrupted.

::: warning Windows only, requires permissions
This feature drives another application's window and is **Windows-only**. On Windows it may need
the app to run with administrator privileges and "monitoring" permissions. It does **not** work in
[Slave mode](/guide/master-slave) (only the Master keys the radio and logs QSOs).
:::

## Settings

In **Settings → Automate tasks**:

| Control | Meaning |
|---|---|
| **Close JTDX Log QSO window prompt** | Enable auto-clicking the JTDX log-confirmation prompt. |
| **Test it** | Trigger a test click to verify it finds the button. |
| **Delay before clicking** (slider, 0–30 s) | Wait this long before clicking — gives you time to intervene or lets the window settle. |
| **Test Windows Monitoring Permissions** | Check that the OS lets the app inspect/click other windows. |

Config keys: `enable_jtdx_autoclick` (prompt close), `jtdx_click_delay`.

## How it works

When enabled, a background timer watches for the JTDX "Log QSO" prompt window. When it appears,
after your configured delay it locates and clicks the **OK / log** button. There is a **fallback**
path if the primary button can't be found (it will try an alternate button position), so layout
variations across JTDX versions are tolerated.

## Tips

- Start with a small **delay** (a few seconds) so you can see it working before trusting it
  unattended.
- Use **Test it** and **Test Windows Monitoring Permissions** after any JTDX update or Windows
  permission change.
- If you run WSJT-X (not JTDX), you can leave this feature off — WSJT-X auto-logs without a modal
  prompt.
