---
title: VoxStream Live Captions
emoji: 🎙️
colorFrom: indigo
colorTo: purple
sdk: gradio
sdk_version: "4.36.0"
app_file: app.py
pinned: false
license: apache-2.0
short_description: Real-time captions powered by VoxCore. Apache-2.0.
---

# VoxStream live caption demo

This Space wraps the [VoxStream](https://github.com/tianjimeteor/VoxCore/tree/main/apps/voxstream)
caption engine in a browser-only Gradio UI.

For OBS / desktop / streaming use, install the native release:

```bash
pip install voxstream
voxstream run
# then open http://localhost:7860/overlay?theme=streaming
```

Engine: [VoxCore](https://github.com/tianjimeteor/VoxCore). License: Apache-2.0.
