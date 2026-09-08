# Bakeshot

[![PyPI](https://img.shields.io/pypi/v/bakeshot)](https://pypi.org/project/bakeshot/)

**Capture the same UI your users see — without a simulator or a device.**

**[bakeshot.vercel.app](https://bakeshot.vercel.app)** · [日本語](https://bakeshot.vercel.app/ja)

## Without Bakeshot

Getting the screens you want means installing the app, opening the right
screen, getting it into the right state, placing the widget, configuring it, getting real
data into it — and only then taking the shot.

| The screenshot you want | What you or your agent has to do first |
|---|---|
| A home screen with a month of history | Seed the database, or tap the data in by hand |
| A seven-day streak | Use the app for seven days running — or forge the dates in storage |
| The paid tier, active | Set up a StoreKit sandbox account and buy through it |
| An empty state, an error state | Wipe the data, or cut the network, and hope nothing else changes |
| A chart that looks good | Keep re-seeding until the numbers happen to make a nice shape |
| The same shots in five languages | Change the device language and take every shot again, five times |
| A widget | Install the app, add the widget, configure it, get data into it, then photograph the home screen and crop |

And you do all of it again next release.

## With Bakeshot

You describe the state in code; Bakeshot builds your app, runs it on your Mac as a real iOS
binary, and draws the view.

```swift
shotBoth("home") { HomeView().environmentObject(thirtyDaysOfHistory()) }
shot("paywall", dark: true) { PlusSheet().environmentObject(PlusStore(active: true)) }
```

Nothing is simulated or mocked up: these are your real views, your real fonts and assets,
rendered by iOS. The app never has to reach the state — the state is handed to it.

It does not decorate. Backgrounds, captions and device frames are somebody else's job
(try [app-store-screenshots](https://github.com/ParthJadhav/app-store-screenshots)).
Bakeshot does the part nobody has automated: **the real UI, in the state that sells it.**

## Use it

```bash
pip install bakeshot
cd MyApp
bakeshot init
```

Then tell your coding agent:

> **Bakeshot を使って App Store Connect 用のプロモーション画像を作成して**
> — or, in English, *"use Bakeshot to create the promotional images for App Store Connect"*

`init` installs a skill into `.claude/skills/bakeshot/`, so the agent reads your models and
views, writes the scene script, runs the render, fixes whatever crashed, and tells you where
the images are. You do not have to learn the flags, or the file, or any of this README.

<details>
<summary>Not using Claude Code?</summary>

Point any agent at the skill: *"Read `.claude/skills/bakeshot/SKILL.md` and follow it."*
Or drive it yourself: edit `Bakeshot/Scenes.swift`, then `bakeshot bake --locale ja --locale en`.

</details>

PNGs land in `Bakeshot/out/<locale>/`, at real store dimensions. Every language is
baked in a single Xcode run — the build happens once, not once per language.

## The scene script

`Bakeshot/Scenes.swift` is where you say what to shoot and in what state. It is plain
Swift against your own types, which is why an agent can write it:

```swift
enum BakeshotScenes {
    @MainActor static var scenes: [BakeshotScene] {
        [
            shotBoth("home_busy") { HomeView().environmentObject(busyStore()) },
            shot("paywall", dark: true) { PlusSheet().environmentObject(PlusStore()) },
            shotBoth("widget", size: .widgetMedium) { MyWidgetView(entry: demoEntry()) },
        ].flatMap { $0 }
    }
}

@MainActor private func busyStore() -> AppStore {
    let s = AppStore()
    s.tags = [Tag(name: "Study"), Tag(name: "Workout"), Tag(name: "Work")]
    s.logs = (0..<20).map { LogEntry(minutes: 30 + $0 * 5) }
    return s
}
```

An empty app makes a worthless screenshot. The state is the product.

## Does it touch my project?

**No.** Bakeshot never edits your files, your `.xcodeproj`, or your git history.

To render your views it needs one test target hosted by your app. Rather than add that
to your project, it works on a hidden throwaway copy of the `.xcodeproj`, and deletes it
when the run ends — including when the run fails. Nothing is left behind.

<details>
<summary>What actually happens</summary>

1. Copy `MyApp.xcodeproj` → `.MyApp-bakeshot.xcodeproj` (hidden, temporary, sits next to
   the original because Xcode projects reference their files by relative path).
2. Add a test target to the copy, hosted by your app.
3. Build the copy for *My Mac (Designed for iPad)* — your iOS binary, running on macOS,
   so Firebase, UIKit, your fonts and assets are all the real thing.
4. Render each scene with `UIHostingController` + `drawHierarchy`, write PNGs.
5. Delete the copy.

</details>

## Requirements

- Apple silicon Mac with Xcode
- `gem install --user-install xcodeproj`
- Your app must be signable with your own team — the setup you already build with

`bakeshot init` checks all of this and tells you what is missing.

## Price

Everything above is free: every screen, every state, every language, every device size.

| | |
|---|---|
| Public | free, forever — app screens |
| Widgets | **$49 / year** |
| Team / agency | **$199 / year** — several projects, CI |
| Launch offer | **$99 once**, first 100 buyers |

The version you paid for keeps working forever; renewing buys the next year of updates.
Xcode breaks this kind of tool roughly once a year — that is what the renewal pays for.

## Known limits

- Xcode is driven while baking, so you cannot use Xcode during a run.
  (`xcodebuild test` cannot launch an iOS-on-Mac test host; the IDE can.)
- A view crashes while rendering if something it demands is missing — nearly always an
  environment object, occasionally a force-unwrapped value that isn't there offline.
  Bakeshot reports the reason and carries on with the rest. Network calls do not crash a
  render; they simply don't finish, so the screen comes out in its loading state.
  Bakeshot names them and bakes the rest — give them fakes in the scene script.
- Widget sources are compiled into the test bundle, so a widget that depends on the
  extension's own asset catalog may render without those images.

## Your data

The throwaway copy is built **without the app's entitlements**. That is deliberate: with them
in place the copy opens the real App Group, and a scene script that happens to run a save or a
sync path would write your live data — and, if the app syncs, push it to your other devices.
Screenshots do not need the real store; the scene hands the views their state instead.

If an app truly cannot launch without its entitlements, `--keep-entitlements` puts them back.
Do that only when the scene script touches nothing that persists.

## License


MIT
