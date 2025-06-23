(function
    name: (identifier) @function)

(call
    callee: (callee) @function)

(extern_directive) @keyword
(entry_directive) @keyword

(variable
    type: (type) @type
    index: (index) @variable)

(macrodigit) @number
(chars) @string
(compound) @string

[
  "="
  ":"
  ","
] @operator

(block_comment) @comment
(line_comment) @comment
(special_comment) @comment

[
  "<"
  ">"
  "("
  ")"
  "{"
  "}"
] @punctuation.bracket

[
  ";"
  "."
] @punctuation.delimiter
