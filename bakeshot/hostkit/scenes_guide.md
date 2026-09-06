# Bakeshot の撮影台本の書き方

`Bakeshot/Scenes.swift` に「何を、どんな状態で撮るか」を Swift で書きます。
Bakeshot はそれを**本物の iOS ランタイム**（My Mac / Designed for iPad）で走らせ、実UIの PNG を書き出します。
シミュレータも UI テストも要りません。

## 形

```swift
import SwiftUI
@testable import __MODULE__

enum BakeshotScenes {
    @MainActor static var scenes: [BakeshotScene] {
        [
            // ライトとダークを 1 行で
            shotBoth("home_busy") {
                HomeView().environmentObject(busyStore())
            },
            // 片方だけなら shot
            shot("paywall_dark", dark: true) {
                PlusSheet().environmentObject(PlusStore())
            },
        ].flatMap { $0 }
    }
}
```

`shot` は 1 枚、`shotBoth` はライト/ダークの 2 枚を返します。
配列に混ぜる時は末尾の `.flatMap { $0 }` を付けたままにしてください
（`shot` は `[BakeshotScene]` ではなく `BakeshotScene` を返すので、混ぜる時は `[shot(...)]` と包みます）。

## 状態を作る

**ここが要点です。** 空のアプリを撮っても売り物になりません。見せたい状態を自分で組み立てます。

```swift
@MainActor private func busyStore() -> AppStore {
    let s = AppStore()
    s.tags = [Tag(name: "勉強"), Tag(name: "運動"), Tag(name: "仕事")]
    s.logs = (0..<20).map { i in LogEntry(tagID: s.tags[i % 3].id, minutes: 30 + i * 5) }
    return s
}
```

アプリの型をそのまま使えます（`@testable import` しているため、internal も見えます）。

## 言語で出し分ける

Bakeshot は言語ごとに焼き直します。台本の中で見せる文言を変えたい時は `Bakeshot.L` を使います。

```swift
shotBoth("home") {
    HomeView().environmentObject(store(title: Bakeshot.L("勉強", "Study")))
}
```

## 焼けない時

- **引数が要る View**: `@State var x: T`（既定値なし）や `@Binding` があると `View()` では作れません。
  `HomeView(x: .init(...))` のように渡してください。
- **描いている最中に落ちる**: 依存（ネットワーク・キーチェーン・環境オブジェクト）が足りていません。
  必要な物を `.environmentObject(...)` / `.environment(...)` で渡すか、その画面を台本から外します。
  Bakeshot は落ちた画面を名指しで外し、残りを焼きます。

## 出来た絵の使い道

言語ごとのフォルダに PNG が出ます。装飾（背景・キャッチコピー・端末フレーム・ストア規定サイズ）は
別の道具に任せてください。例: https://github.com/ParthJadhav/app-store-screenshots