---
title: "How to Run a Batch Script When Your Battery Hits a Certain Percentage"
seo_title: Run a Batch Script When Your Battery Hits X%
slug: run-bat-script-when-battery-percentage
date: 2026-10-30
description: "Running a .bat when the battery drops below a set level is easy in PowerShell and a minefield of silent failures. The working version, plus the gotchas."
keywords: "run bat script when battery low, windows battery threshold script, batch script on low battery, task scheduler battery level trigger"
tags: [Automation, Battery Alerts, Windows 11]
---

There is a moment in most people's working day where the laptop battery stops being a background detail and becomes the whole problem. You are forty minutes into something, the charger is three rooms away, and you would give a lot for the machine to do *something* — run your backup script, fire off a notification to your phone, sync the folder you were just working in.

Windows does not let you attach an action to a battery percentage. There is no "when battery drops below 20%, run this" switch anywhere in Settings. But it is a short script, and once you have it, you can hang anything you like off that trigger.

Here is the working version, and then the handful of reasons it silently does nothing.

## The short version

Save this as `battery-guard.ps1`:

```powershell
param(
    [int]$Threshold = 20,
    [string]$Script = "C:\Scripts\on-low-battery.bat"
)

$log = Join-Path $PSScriptRoot "battery-guard.log"

function Write-Log([string]$Message) {
    "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')  $Message" |
        Out-File -FilePath $log -Append
}

while ($true) {
    $battery = Get-CimInstance -ClassName Win32_Battery -ErrorAction SilentlyContinue |
               Select-Object -First 1

    if ($null -eq $battery) {
        Write-Log "No battery detected. Exiting."
        break
    }

    # BatteryStatus 1 = discharging, 2 = on AC power
    $onBattery = $battery.BatteryStatus -eq 1
    $level     = [int]$battery.EstimatedChargeRemaining

    if ($onBattery -and $level -le $Threshold) {
        Write-Log "Battery at $level% - running $Script"
        & $Script
        Write-Log "Script finished, exit code $LASTEXITCODE"
        break
    }

    Start-Sleep -Seconds 30
}
```

Run it once by hand to be sure, then wire it to start with Windows (Task Scheduler → **Create Task** → General tab → tick **Run whether user is logged on or not** → Triggers tab → **At startup**).

That is the whole idea. Everything below is what goes wrong when you try to make it reliable.

## Why the obvious version fails

Most published scripts in this space look almost identical to the one above and then do absolutely nothing on the user's machine. Five causes, roughly in order of how often they bite.

### 1. There is no battery, so there is no object to read

`Get-CimInstance Win32_Battery` returns nothing on a desktop or a laptop with the battery removed. A script without a null check then dereferences `$null` and either throws on the first line or, worse, quietly evaluates the comparison as false forever.

The `if ($null -eq $battery)` guard is not defensive programming noise. It is the single most common reason a battery script "does not work" on a machine the author never tested on.

### 2. Task Scheduler does not run your script from your script folder

The default working directory for a scheduled task is `C:\Windows\System32`. Any relative path in your `.bat` — including relative paths to the `.bat` itself — resolves somewhere else entirely. This is why a script that ran perfectly when you double-clicked it fails at 3am.

Two fixes: use absolute paths everywhere, or put `Set-Location $PSScriptRoot` at the top of the PowerShell script. Absolute paths are less clever and more reliable.

### 3. Task Scheduler kills your loop after three days

The default "Stop the task if it runs longer than" limit is 72 hours. A `while ($true)` polling loop will be terminated on day three, quietly, and never start again.

In the Task Scheduler UI: **Settings tab** → tick **If the task is running, do not stop it** → "Stop the task if it runs longer than" → set to 1 hour (or tick "Do not stop the task"). In the XML this is `<ExecutionTimeLimit>PT0S</ExecutionTimeLimit>`.

### 4. "Run whether user is logged on or not" is not who you think it is

This is the one that catches everybody. The option runs the task **as the user account** but *without* that user's session — no mapped network drives, no `C:\Users\You\Desktop`, no access to anything that needs your interactive login.

Tick it and your script loses your drive letters. Leave it unticked and the task only runs while you are logged in, which defeats the purpose.

The clean answer is to run the task as **SYSTEM** (System account, run with highest privileges). SYSTEM sees the whole filesystem. The cost is that SYSTEM has no network drive mappings, so anything in your script that touches `Z:\` needs to map it explicitly first.

### 5. The percentage is an estimate, not a measurement

`EstimatedChargeRemaining` is a number the firmware reports. It is usually an integer, it can lag reality, and on some machines it does not update at all while the battery is above 20%. It is close enough for a threshold trigger, but do not build anything precise on top of it — and do not expect it to match the Windows battery icon to the digit.

Also add the `BatteryStatus -eq 1` check. Without it, the script fires on a full battery sitting on the charger, because 100% is not below 20% only by accident of the comparison direction.

## The event-driven version, if you want to skip polling

Polling every thirty seconds is not elegant. WMI can tell you when the battery object actually changes, instead of you asking it constantly:

```powershell
$Threshold = 20

Register-CimEvent -Query @"
    SELECT * FROM __InstanceModificationEvent WITHIN 15
    WHERE TargetInstance ISA 'Win32_Battery'
"@ -Action {
    $b = $Event.SourceEventArgs.NewEvent.TargetInstance
    if ($b.BatteryStatus -eq 1 -and [int]$b.EstimatedChargeRemaining -le $Threshold) {
        & "C:\Scripts\on-low-battery.bat"
    }
}
```

The `WITHIN 15` is the sampling window WMI uses to detect changes — it is still periodic under the hood, but the event only fires when something actually moved.

Two caveats. `Register-CimEvent -Action` blocks run in their own scope, so variables from the enclosing script are not always visible inside them; pass the threshold in explicitly or read it from a file. And this still needs a long-lived PowerShell process, so it does not escape the need for a startup task.

You can also register the same query directly in Task Scheduler, which removes the long-lived process entirely. Export a task to XML, and inside `<Triggers>` put:

```xml
<WmiEventTrigger>
  <Query>
    <![CDATA[
      SELECT * FROM __InstanceModificationEvent WITHIN 60
      WHERE TargetInstance ISA 'Win32_Battery'
    ]]>
  </Query>
</WmiEventTrigger>
```

Then the task fires on the event, runs once, and exits. No loop, no three-day limit, no orphaned PowerShell session.

## What to actually run when it fires

The trigger is the easy half. Here are three `.bat` files worth having.

**Notify yourself properly.** A beep on a laptop in another room is a beep you will not hear. Push it somewhere you will:

```bat
@echo off
powershell -NoProfile -Command ^
  "New-BurntToastNotification -Text 'Battery low' -Message 'Plug in now - %computername%' -Sound 'Warning'"
```

`New-BurntToastNotification` is from the free BurntToast module (`Install-Module BurntToast`). Swap it for a `curl` call to a webhook if you run a local home server.

**Back up the work you have not saved.** A tool that grabs whatever you were working in, before the machine decides it is done:

```bat
@echo off
robocopy "C:\Users\%USERNAME%\Documents\Work" "Z:\Backups\work" /MIR /R:1 /W:1 /LOG+:"C:\Scripts\backup.log"
```

`/MIR` mirrors, so deleted files get removed on the destination too — make sure that is what you want before pointing it at anything you care about.

**Log it, so you can prove when it fired.** The habit of writing a timestamped line costs nothing and saves a lot of guessing later:

```bat
@echo off
echo %date% %time% battery threshold reached >> C:\Scripts\trigger.log
```

## The part that bites: scripts that will not stop

Here is the failure mode that makes people give up on this approach entirely.

A `.bat` file that starts a long-running process and returns immediately leaves that process running. Task Scheduler considers the task finished, the battery script carries on, and you end up with orphaned copies of whatever it launched. Worse, nothing stops them when the battery situation resolves — the backup runs again, the notification fires again, and eventually something is fighting over the same file.

Fixing this by hand means tracking process IDs and killing process trees, which is exactly the sort of bookkeeping a small utility should be doing for you.

[Battery Alert Pro](/#download) runs a `.bat` directly from its settings window: pick **Run Bat Script**, browse to the file, and set the behaviour. The part worth knowing is the duration. As the manual puts it, *"If a duration is set, the script and any processes it started will be terminated when the time is up."* Not just the script — the child processes it spawned. You set a threshold, the alert runs, your script runs, and when the timer expires the whole tree is cleaned up.

The other half of that screen is the **Finally** action, and it is the reason this beats doing it by hand. Your script can start a five-minute backup at 20%, and then the machine sleeps or shuts down on purpose once the backup finishes — with the work saved and the outcome announced, instead of Windows pulling the plug at 5% while your script is still writing.

If you only ever run one thing on a battery threshold, run something that saves your work. Everything else is optional.

## A checklist before you trust it

- Run it manually first, with the threshold set high enough to trigger immediately — confirm the `.bat` path is right
- Add the null check for no battery
- Use absolute paths, or `Set-Location $PSScriptRoot`
- Set the task's execution time limit to unlimited
- Decide deliberately between running as your user (needs a password, loses drive mappings) or as SYSTEM (sees everything, no network drives)
- Add a log line so you can tell "it did not fire" from "it fired and the script failed"
- Check the event that your script starts has actually stopped before the next threshold — or let a tool with a duration handle it

More on the notification side of this, including why a Windows toast in the corner of the screen is not a warning, in [the post on what the default battery alerts actually do](/posts/windows-battery-warning-10-percent/). And if the real problem is that you work in long blocks where any interruption costs you an hour, that is worth reading about separately too: [ADHD and lost work](/posts/adhd-laptop-shutdown-lost-work/).
