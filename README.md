# Bakeshot

**Real App Store screenshots from your Xcode project. No simulator. No UI tests.**

https://github.com/user-attachments/assets/6a902e87-bb5d-467f-8c55-96d89f550ac3

## Use it

```bash
pip install bakeshot
cd MyApp
bakeshot init
```

Then tell your coding agent:

> **App Store 用のスクショを作って** — or, in English, *"make the App Store screenshots"*

`init` installs a skill into `.claude/skills/bakeshot/`, so the agent reads your models and
views, writes the scene script, runs the render, fixes whatever crashed, and tells you where
the images are. You do not have to learn the flags, or the file, or any of this README.

<details>
<summary>Not using Claude Code?</summary>

Point any agent at the skill: *"Read `.claude/skills/bakeshot/SKILL.md` and follow it."*
Or drive it yourself: edit `Bakeshot/Scenes.swift`, then `bakeshot bake --locale ja --locale en`.

</details>

PNGs land in `Bakeshot/out/<locale>/`, at real store dimensions.

## What it does

Bakeshot builds your iOS app, runs it on your Mac as a real iOS binary, and renders your
actual SwiftUI views — every screen, every language, light and dark, widgets included.

It does not decorate. Backgrounds, captions and device frames are somebody else's job
(try [app-store-screenshots](https://github.com/ParthJadhav/app-store-screenshots)).
Bakeshot only does the part nobody has automated: **capturing the real UI**.

## Why

`fastlane snapshot` works, but you have to write UI tests, keep them alive, and boot
simulators. Most people give up and take screenshots by hand — then do it again next
release, times every language, times every device size.

There is no simulator and no UI test here. Your views are rendered directly, from your
real code, with the state you asked for.

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

The public version renders at 6.9" (1320×2868). That is enough to ship an iPhone listing,
and enough to see it work on your own app.

| | |
|---|---|
| Public | free, forever — 6.9" |
| Full | **$49 / year** — 6.7 / 6.5 / 6.3 as well, and widgets |
| Team / agency | **$199 / year** — several projects, CI |
| Launch offer | **$99 once**, first 100 buyers |

The version you paid for keeps working forever; renewing buys the next year of updates.
Xcode breaks this kind of tool roughly once a year — that is what the renewal pays for.

## Known limits

- Xcode is driven while baking, so you cannot use Xcode during a run.
  (`xcodebuild test` cannot launch an iOS-on-Mac test host; the IDE can.)
- Screens that need network, keychain or a live account crash while rendering.
  Bakeshot names them and bakes the rest — give them fakes in the scene script.
- Widget sources are compiled into the test bundle, so a widget that depends on the
  extension's own asset catalog may render without those images.

## License

MIT
