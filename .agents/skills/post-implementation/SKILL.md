---
name: post-implementation
description: Load this skill upon finishing an implementation that was approved by the user to document it.
last_updated: 2026-04-29 14:59
---
Write a short document — ~40 lines — about how the implementations went, the decisions made (the "why"s), any challenges encountered, and — if it exists at all — any drift from the plan. Include no code snippets or line numbers, only references to files and symbols. 

Don't just explain in words what can be obviously inferred from reading the actual source files. This is redundant, like repeating the same information once in JavaScript and again in English. Make your result complementary to the source code so there is added value in reading it that couldn't be gained from just reading the source. 

Also, bidirectionally link the plan file and the Markdown file you write via the YAML front matter.

If you've been drawing from a plan file, there should be a directory in its vicinity where implementation docs live. 
