# Writing the scene script (for coding agents)

You are editing `Bakeshot/Scenes.swift` in this repository. It decides **which screens
Bakeshot renders, and in what state**. Bakeshot then builds the app, runs it on the Mac
as a real iOS binary, and writes the screens out as PNGs at store dimensions.

## The shape

```swift
import SwiftUI
@testable import __MODULE__

enum BakeshotScenes {
    @MainActor static var scenes: [BakeshotScene] {
        [
            shotBoth("home") { HomeView().environmentObject(demoStore()) },
            shot("paywall", dark: true) { PlusSheet().environmentObject(PlusStore()) },
            shotBoth("widget", size: .widgetMedium) { MyWidgetView(entry: demoEntry()) },
        ].flatMap { $0 }
    }
}
```

- `shot(name, dark:, size:) { view }` → one image
- `shotBoth(name, size:) { view }` → light and dark (`_light` / `_dark` suffixes)
- `size:` defaults to the phone screen. Widgets need `.widgetSmall` / `.widgetMedium` /
  `.widgetLarge` / `.widgetExtraLarge`, or `.custom(w, h)`.
- The array mixes single and pair entries, so keep the trailing `.flatMap { $0 }`
  and wrap single `shot(...)` calls as `[shot(...)]` when mixing.

## The part that matters: state

An empty app makes a worthless screenshot. Build the state you want to show, using the
app's own types (`@testable import` makes internal types visible):

```swift
@MainActor private func demoStore() -> AppStore {
    let s = AppStore()
    s.tags = [Tag(name: "Study"), Tag(name: "Workout"), Tag(name: "Work")]
    s.logs = (0..<20).map { LogEntry(tagID: s.tags[$0 % 3].id, minutes: 30 + $0 * 5) }
    return s
}
```

Read the app's models and view initialisers before writing this. Prefer realistic,
flattering data: a few days of history, a streak in progress, a chart with shape.

## Language

Every locale is rendered in one run: Bakeshot walks the script once per language,
setting `Bakeshot.locale` before each pass. SwiftUI's own `Text("key")` follows along,
because the locale is set on the view's environment.

Use `Bakeshot.L(ja, en)` when the demo data itself should differ per language:

```swift
shotBoth("home") { HomeView().environmentObject(store(title: Bakeshot.L("勉強", "Study"))) }
```

If the app switches language through its own manager, call it **inside the scene body**
— it runs again for every language:

```swift
shotBoth("home") {
    Localizer.setLanguage(Bakeshot.isJa ? .ja : .en)   // 各言語で呼び直される
    return HomeView()
}
```

Apps that read the process language instead (`NSLocalizedString`, `Bundle.main`) will not
switch mid-run. Those need `bakeshot bake --locale-per-run`, which rebuilds per language.

## Rules

- Only views you can construct here. A view with `@Binding`, `@ObservedObject`, or a
  `@State` without a default needs its arguments passed explicitly.
- Views that hit the network, keychain or a signed-in account will crash while
  rendering. Inject fakes, or leave those screens out.
- Do not modify the app's own source to make this work. Everything belongs in this file.
- Name shots for what they show (`home_busy`, `stats_week`), not for the type name.

## Checking your work

```bash
bakeshot bake
```

Bakeshot names any scene that fails to compile or crashes while rendering, and still
writes the rest. Fix those scenes here and run again.
