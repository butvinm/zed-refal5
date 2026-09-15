; A construct split across lines continues one level deeper than the line it starts on,
; and its closing bracket returns to the indentation of that line.

(function "{" @start "}" @end) @indent
(call_block "{" @start "}" @end) @indent

; Lines after the pattern (`,` `:` `=`) are one level deeper than the pattern
(sentence) @indent

; A result or condition result continued past its `=` or `,` line, with `:` back at the `,` level
(return "=" @start) @indent
(condition "," @start ":" @end) @indent
(call_block "," @start ":" @end) @indent

(call "<" ">" @end) @indent
(brackets "(" ")" @end) @indent
