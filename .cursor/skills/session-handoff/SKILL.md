---
name: session-handoff
description: >-
  Take over from a previous Claude session (container restart, replaced session): read its transcript cheaply,
  find its working files and pending questions, and carry on without redoing its work.
---

# Take over from a previous session

1. **Extract the conversation, not the raw JSONL** (transcripts are 10+ MB; `jq` may be missing). One pass writes the
   user/peer messages, the assistant's text and a one-line summary of each tool call to a scratch file:

   ```bash
   python3 - <<'EOF2' > "$SCRATCH/convo.txt"
   import json, sys
   for line in open(sys.argv[1] if len(sys.argv) > 1 else "TRANSCRIPT.jsonl"):
       try: d = json.loads(line)
       except ValueError: continue
       if d.get("type") not in ("user", "assistant"): continue
       c, ts = d["message"].get("content"), d.get("timestamp", "")
       for b in ([{"type": "text", "text": c}] if isinstance(c, str) else c or []):
           if b.get("type") == "text": print(f"\n=== {d['type']} {ts}\n{b['text']}")
           elif b.get("type") == "tool_use": print(f"--- tool {ts} {b['name']}: {json.dumps(b['input'])[:300]}")
   EOF2
   ```
   (replace `TRANSCRIPT.jsonl` with the path). Then `grep -n '^=== user' convo.txt | tail` and read from the last
   few user/peer messages to the end, filtering out the `--- tool` lines. The final assistant message usually lists
   what is pending.
2. **Find the exact commands it used** instead of re-deriving them: load the JSONL in Python again and print the
   full `input.command` of `Bash` tool calls whose text contains a keyword (a script name, a section number).
3. **Find its working files:** tool calls that write (`Write`, `cp`, `> file`) name them; its scratchpad
   (`/tmp/claude-0/<project>/<session id>/scratchpad`) often survives a restart in the same container.
4. **Check what it left uncommitted** (`git status`, `git diff --ignore-cr-at-eol --stat`) and whether its background
   jobs finished (their `tasks/*.output` files).
5. Read memory and the project's rules before acting; then do the work in the order you were given.
