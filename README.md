# Bakeshot

**App Store screenshots of your real UI — in states your app has never actually been in.**
No simulator. No UI tests.

https://github.com/user-attachments/assets/6a902e87-bb5d-467f-8c55-96d89f550ac3

## Without Bakeshot

A store screenshot is only worth taking if the app is showing something good. But to
photograph a screen, the app has to *actually be* in that state — so you, or the agent you
asked, has to put it there first:

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
binary, and draws the view. A month of history is four lines. The paid tier is one
initialiser. Five languages is one flag.

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

> **Bakeshot で App Store 用のスクショを作って**
> — or, in English, *"make the App Store screenshots with Bakeshot"*

`init` installs a skill into `.claude/skills/bakeshot/`, so the agent reads your models and
views, writes the scene script, runs the render, fixes whatever crashed, and tells you where
the images are. You do not have to learn the flags, or the file, or any of this README.

<details>
<summary>Not using Claude Code?</summary>

Point any agent at the skill: *"Read `.claude/skills/bakeshot/SKILL.md` and follow it."*
Or drive it yourself: edit `Bakeshot/Scenes.swift`, then `bakeshot bake --locale ja --locale en`.

</details>

PNGs land in `Bakeshot/out/<locale>/`, at real store dimensions.

## Why not fastlane snapshot

`fastlane snapshot` drives a simulator through UI tests. It can only photograph states your
app can reach by tapping — and you write and maintain the taps. Getting to "thirty days of
history, paid tier, in German" means seeding a database, signing in, and switching the
device language, every release.

Bakeshot does not tap anything. It constructs the state and renders the view.

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

**Widgets are the paid part** — the one screenshot you genuinely cannot take by hand.
An app screen you can at least reach by tapping. A widget means installing the app,
placing the widget, configuring it, getting real data into it, photographing the home
screen and cropping. Bakeshot renders it directly, in the state you asked for, at the
exact store size.

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
- Screens that need network, keychain or a live account crash while rendering.
  Bakeshot names them and bakes the rest — give them fakes in the scene script.
- Widget sources are compiled into the test bundle, so a widget that depends on the
  extension's own asset catalog may render without those images.

## License

MIT
