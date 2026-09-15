(function
  scope: (entry_directive)? @context
  name: (identifier) @name) @item

; Comments right above a function, such as its doc comment, annotate it
(program
  [
    (block_comment)
    (line_comment)
  ] @annotation)
