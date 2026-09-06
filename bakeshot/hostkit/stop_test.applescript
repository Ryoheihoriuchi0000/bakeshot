-- Bakeshot: 走っているテストを止める。引数に close を渡すとプロジェクトも閉じる。
on run argv
    set projPath to item 1 of argv
    set doClose to ((count of argv) > 1 and item 2 of argv is "close")
    set AppleScript's text item delimiters to "/"
    set projName to last text item of projPath
    set AppleScript's text item delimiters to ""
    tell application "Xcode"
        try
            try
                set ws to first workspace document whose path is projPath
            on error
                -- start 側と同じ理由。Xcode の返す path は渡した文字列と違うことがある
                set ws to first workspace document whose name is projName
            end try
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
