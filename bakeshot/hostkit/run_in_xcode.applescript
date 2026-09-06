-- 使い方: osascript run_in_xcode.applescript <xcodeproj path> <scheme>
-- ⚠ 呼ぶ前に、その xcodeproj を Xcode で開いていない状態にしておく（開いたまま作り直すと「別のアプリが変更」ダイアログで止まる）
on run argv
    set projPath to item 1 of argv
    set schemeName to item 2 of argv
    tell application "Xcode"
        open projPath
        set ws to missing value
        -- パッケージが多いプロジェクトは開くのに数分かかる（Ice Cubes: SPM 20個）。
        -- ⚠ `loaded` はパッケージ解決の間 false のまま返ることがある。スキームが見えたら準備できたとみなす
        set isLoaded to false
        repeat 450 times
            try
                set ws to first workspace document whose path is projPath
                if loaded of ws then
                    set isLoaded to true
                    exit repeat
                end if
                if (count of (schemes of ws whose name is schemeName)) > 0 then
                    set isLoaded to true
                    exit repeat
                end if
            end try
            delay 2
        end repeat
        if not isLoaded then return "error: not loaded in time"
        set active scheme of ws to (first scheme of ws whose name is schemeName)
        try
            set active run destination of ws to (first run destination of ws whose name contains "Designed for")
        end try
        set r to test ws
        repeat 360 times
            if completed of r then exit repeat
            delay 5
        end repeat
        set outcome to "completed: " & (completed of r as string) & " status: " & (status of r as string)
        close ws saving no
        return outcome
    end tell
end run
