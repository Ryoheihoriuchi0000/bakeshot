# Kiln

**Real App Store screenshots from your Xcode project. No simulator. No UI tests.**

https://github.com/user-attachments/assets/PLACEHOLDER

```bash
kiln bake --locale ja --locale en
```

Kiln builds your iOS app, runs it on your Mac, and renders your actual SwiftUI views
to PNGs at App Store sizes — every screen, every language, light and dark, widgets included.

It does not decorate. Backgrounds, captions and device frames are somebody else's job
(try [app-store-screenshots](https://github.com/ParthJadhav/app-store-screenshots)).
Kiln only does the part nobody has automated: **capturing the real UI**.

## Why

`fastlane snapshot` works, but you have to write UI tests, keep them alive, and boot
simulators. Most people give up and take screenshots by hand — then do it again next
release, times every language, times every device size.

Kiln skips all of that. There is no simulator and no UI test. Your views are rendered
directly, from your real code, with your real data.

## How you use it

```bash
pip install kiln-shots
cd MyApp
kiln doctor      # checks Xcode, Ruby, the xcodeproj gem
kiln init        # writes Kiln/Scenes.swift (a draft) and a guide
kiln bake        # renders it
```

`kiln init` leaves a **scene script** in your repo. That is where you say *what to shoot
and in what state* — in Swift, using your own types:

```swift
enum KilnScenes {
    @MainActor static var scenes: [KilnScene] {
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

This is the point of Kiln. An empty app makes a worthless screenshot; the state is what
sells. And because the script is plain Swift next to your code, **your coding agent can
write it** — "shoot the home screen with four tags and three hours logged today, dark
mode" is a request Claude Code or Cursor can turn into the code above. The guide Kiln
drops in `Kiln/台本の書き方.md` is written for exactly that.

Output lands in `Kiln/out/<device>/<locale>/<name>.png` at real store dimensions
(6.9" → 1320×2868, 6.5" → 1242×2688, and so on).

## How it works

1. Copies your `.xcodeproj` to `YourApp-Kiln.xcodeproj` and adds an XCTest target hosted
   by your app. Your project is never modified.
2. Builds it for **My Mac (Designed for iPad)** — your iOS binary, running on macOS.
   Firebase, UIKit, your fonts and assets are all the real thing.
3. Renders each scene with `UIHostingController` + `drawHierarchy` and writes PNGs.
4. Collects them, and drops any screen that crashes while rendering so the rest still ship.

Because the app runs as a real iOS binary, what you get is iOS rendering — not a macOS
approximation.

## Requirements

- Apple silicon Mac with Xcode
- `gem install --user-install xcodeproj`
- Your app must be signable with your own team (the same setup you already build with)

`kiln doctor` checks all of this and tells you what is missing.

## Known limits

- Xcode is driven while baking, so you cannot use Xcode during a run.
  (`xcodebuild test` cannot launch an iOS-on-Mac test host; the IDE can. This is a
  workaround for that, not a preference.)
- Screens that need network, keychain or a live account may crash while rendering.
  Kiln names them and bakes the rest — give them what they need in the scene script.
- Widgets are supported, but their sources are compiled into the test bundle, so a widget
  that depends on the extension's own asset catalog may render without those images.

## License

MIT
