#!/usr/bin/env python3
"""Stand-in for yt-dlp in the tests: records its arguments and prints a fixture.

FAKE_YTDLP_ARGS names a file that receives the arguments as JSON, and FAKE_YTDLP_OUTPUT a JSON
file printed the way --dump-json prints: one object per line, a list as one line per item.
"""

import json
import os
import sys

with open(os.environ["FAKE_YTDLP_ARGS"], "w", encoding="utf-8") as args_file:
    json.dump(sys.argv[1:], args_file)

with open(os.environ["FAKE_YTDLP_OUTPUT"], encoding="utf-8") as output_file:
    data = json.load(output_file)

for item in data if isinstance(data, list) else [data]:
    sys.stdout.buffer.write((json.dumps(item, ensure_ascii=False) + "\n").encode("utf-8"))
