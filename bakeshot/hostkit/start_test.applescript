-- Bakeshot: Xcode でテストを開始して**すぐ返る**。完了は Bakeshot が進捗ファイルで見張る。
-- 使い方: osascript start_test.applescript <xcodeproj path> <scheme>
-- ⚠ 開いたまま xcodeproj を作り直すと「別のアプリが変更」ダイアログで止まる。作り直す前に stop_test で閉じる
on run argv
    set projPath to item 1 of argv
    set schemeName to item 2 of argv
    tell application "Xcode"
        open projPath
        set ws to missing value
        set isReady to false
        -- パッケージが多いと開き切るまで数分。`loaded` は解決中 false のままなので、スキームが見えたら可とする
        repeat 450 times
            try
                set ws to first workspace document whose path is projPath
                if loaded of ws then
                    set isReady to true
                    exit repeat
                end if
                if (count of (schemes of ws whose name is schemeName)) > 0 then
                    set isReady to true
                    exit repeat
                end if
            end try
            delay 2
        end repeat
        if not isReady then return "error: not loaded in time"
        set active scheme of ws to (first scheme of ws whose name is schemeName)
        try
            set active run destination of ws to (first run destination of ws whose name contains "Designed for")
        end try
        test ws
        return "started"
    end tell
end run
