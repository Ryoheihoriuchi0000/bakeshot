---
name: bakeshot
description: Make App Store screenshots of this app — real UI, real data, every language and device size. Use when the user asks for screenshots, store assets, App Store images, スクショ, or says they are preparing a release. Runs Bakeshot, which renders the app's actual SwiftUI views without a simulator or UI tests.
---

# Making App Store screenshots with Bakeshot

You do the whole job. The user should only have to ask once.

## 1. Set up (once per project)

```bash
bakeshot init
```

This creates `Bakeshot/Scenes.swift` (a draft) and `Bakeshot/bakeshot.json`. If it reports
something missing (Xcode, the `xcodeproj` gem), fix or explain it before going on.

## 2. Read the app, then write the scene script

Open `Bakeshot/Scenes.swift`. The draft lists whatever views happened to be constructible;
it renders them **empty**, which is useless for a store listing. Replace it.

Before writing, read the app's models and views to learn:
- which screens a new user would be sold by (home with data, the main list, stats, paywall)
- the types needed to build state (`AppStore`, `Tag`, `LogEntry`, view models…)
- what each view's initialiser requires

Then write scenes that show the app **in use**:

```swift
import SwiftUI
@testable import MyApp

enum BakeshotScenes {
    @MainActor static var scenes: [BakeshotScene] {
        [
            shotBoth("home") { HomeView().environmentObject(busy()) },
            shotBoth("stats") { StatsView().environmentObject(busy()) },
            shot("paywall", dark: true) { PlusSheet().environmentObject(PlusStore()) },
        ].flatMap { $0 }
    }
}

@MainActor private func busy() -> AppStore {
    let s = AppStore()
    s.tags = [Tag(name: "Study"), Tag(name: "Workout"), Tag(name: "Work")]
    s.logs = (0..<24).map { LogEntry(tagID: s.tags[$0 % 3].id, minutes: 25 + $0 * 7) }
    return s
}
```

Rules:
- `shot(name, dark:, size:)` = one image. `shotBoth(name, size:)` = light + dark.
- Keep the trailing `.flatMap { $0 }`; wrap lone `shot(...)` calls as `[shot(...)]` when mixing.
- Widgets need an explicit size: `.widgetSmall` / `.widgetMedium` / `.widgetLarge` /
  `.widgetExtraLarge`. Build the entry the way the app's `TimelineProvider` does.
- Use `Bakeshot.L(ja, en)` when demo data itself should differ per language.
- Never edit the app's own source to make a scene work. Everything belongs in this file.

Data quality is the job. A few days of history, a streak in progress, a chart with shape,
realistic names. An empty screen is a wasted screenshot.

## 3. Bake

```bash
bakeshot bake --locale ja --locale en
```

Add `--device 6.9 --device 6.5` if the full version is installed (`bakeshot status` says).

## 4. Fix what failed, then bake again

Bakeshot names every scene it could not build or that crashed while rendering:

- **"引数が要るので外しました"** — the view needs arguments. Pass them explicitly.
- **"焼いている最中に落ちた"** — the view hit the network, keychain or a missing
  environment object. Inject a fake, or drop that scene.

Fix `Bakeshot/Scenes.swift` and run `bakeshot bake` again. Repeat until the set is complete
or a screen is genuinely un-renderable — then say so plainly.

## 5. Report

Tell the user how many images landed in `Bakeshot/out/<locale>/`, what each one shows, and
which screens were dropped and why. Do not describe the internals unless asked.

## Notes

- Bakeshot never modifies the user's project. It works on a hidden throwaway copy of the
  `.xcodeproj` and deletes it afterwards.
- A run drives Xcode for a minute or two; Xcode cannot be used meanwhile. Say so before
  starting if the user is working.
- Bakeshot does not decorate. Backgrounds, captions and device frames are a separate step.
