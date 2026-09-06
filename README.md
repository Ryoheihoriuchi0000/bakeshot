# Bakeshot

**Real App Store screenshots from your Xcode project. No simulator. No UI tests.**

https://github.com/user-attachments/assets/6a902e87-bb5d-467f-8c55-96d89f550ac3

## Use it

```bash
pip install bakeshot
cd MyApp
bakeshot init
```

`init` prints one sentence to paste into your coding agent:

> Read `Bakeshot/AGENT.md` and write the scene script in `Bakeshot/Scenes.swift`.
> Home screen with data in it, settings, and the paywall, in light and dark.

Your agent writes the script. Then:

```bash
bakeshot bake --locale ja --locale en
```

PNGs land in `Bakeshot/out/<locale>/`, at real store dimensions.
That is the whole tool: **two commands and one sentence.**

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

## How it works

1. Copies your `.xcodeproj` to `YourApp-Bakeshot.xcodeproj` and adds an XCTest target
   hosted by your app. **Your project is never modified.**
2. Builds it for *My Mac (Designed for iPad)* — your iOS binary, running on macOS.
   Firebase, UIKit, your fonts and assets are all the real thing.
3. Renders each scene with `UIHostingController` + `drawHierarchy`.
4. Collects the PNGs, and names any screen that crashes so the rest still ship.

## Requirements

- Apple silicon Mac with Xcode
- `gem install --user-install xcodeproj`
- Your app must be signable with your own team — the setup you already build with

`bakeshot init` checks all of this and tells you what is missing.

## Device sizes

`--device 6.9` (default, 1320×2868), `6.7`, `6.5`, `6.3`. Repeat the flag for several.

## Price

Three days of use are free — days you actually run `bake`, not calendar days.
After that, `bakeshot activate <key>` unlocks it.

| | |
|---|---|
| Solo | **$49 / year** — the version you paid for keeps working forever; renewing buys the next year of updates |
| Team / agency | **$199 / year** — several projects, CI |
| Launch offer | **$99 once**, first 100 buyers |

Xcode breaks this kind of tool roughly once a year. That is what the renewal pays for.

## Known limits

- Xcode is driven while baking, so you cannot use Xcode during a run.
  (`xcodebuild test` cannot launch an iOS-on-Mac test host; the IDE can.)
- Screens that need network, keychain or a live account crash while rendering.
  Bakeshot names them and bakes the rest — give them fakes in the scene script.
- Widget sources are compiled into the test bundle, so a widget that depends on the
  extension's own asset catalog may render without those images.

## License

MIT
