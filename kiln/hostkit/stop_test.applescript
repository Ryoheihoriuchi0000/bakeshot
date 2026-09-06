-- Kiln: 走っているテストを止める。引数に close を渡すとプロジェクトも閉じる。
on run argv
    set projPath to item 1 of argv
    set doClose to ((count of argv) > 1 and item 2 of argv is "close")
    tell application "Xcode"
        try
            set ws to first workspace document whose path is projPath
            try
                stop ws
            end try
            if doClose then
                delay 1
                close ws saving no
            end if
        end try
    end tell
    return "stopped"
end run
