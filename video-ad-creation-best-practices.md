# Video Ad Creation Best Practices

Reference for the 8-part prompt framework used in the video session form (Advanced mode).

---

## 1. Master the Prompt Engineering Framework

**Be Specific and Descriptive:** Instead of generic descriptions, use rich details covering the subject, action, context, and style.

**The 8-Part Framework:** A professional video prompt should include:

| # | Element | Description | Example |
|---|---------|-------------|---------|
| 1 | **Scene** | One-sentence summary of the action/vibe | "A parent and student celebrate SAT score improvement at kitchen table" |
| 2 | **Visual Style** | Cinematic, realistic, animated, or camera type | "UGC realistic, shot on phone, natural grain" |
| 3 | **Camera Movement** | Explicit motion direction | "slow dolly-in", "handheld tracking", "static medium shot" |
| 4 | **Subject & Action** | Who/what is in the scene and what they're doing | "High school student opens laptop, smiles at practice test score" |
| 5 | **Background/Setting** | Time of day, weather, environment | "Bright home study area, afternoon sunlight through window" |
| 6 | **Lighting & Mood** | Lighting style and emotional tone | "Natural soft light, warm and encouraging" |
| 7 | **Audio Cues** | Sound effects, music, dialogue | "Ambient room tone, no dialogue, no music" or "upbeat background music" |
| 8 | **Color Palette** | Warm, cool, brand-specific | "Brand teal (#17e2ea), navy (#0a2240), warm whites" |

**Structure for Success:** Put key elements (subject/action) first. Keep prompts to 3-6 sentences or 100-150 words.

**Negative Prompts:** Specify what to avoid: "no text", "no subtitles", "no brand logos", "no cars". Kling 2.6 supports `negative_prompt` as a separate API parameter.

---

## 2. Focus on Visual Consistency

- **Standardized Descriptions:** For character consistency, use an identical, detailed text description of their appearance (hair, clothes, build) in every prompt, changing only the action.
- **Repeat Key Phrases:** Use the same description for the environment/character to "glue" shots together across variants.
- **Image-to-Video (future):** Kling supports I2V — start with a reference image and use the text prompt only to describe the motion.

---

## 3. Leverage Cinematic and Technical Controls

- **Camera Framing:** Use industry terms: Close-up (CU) for emotion, Medium Shot (MS) for interaction, Wide Shot (WS) for environment.
- **Lighting as Mood:** "Volumetric lighting", "backlighting for silhouette", "soft morning sunlight".
- **Control Pacing:** Keywords like "slow motion", "time-lapse", "energetic" dictate tempo.
- **Optimal Ratios:** 9:16 for social media (Reels/Stories), 16:9 for YouTube/Web, 1:1 for feed.

---

## 4. Audio Best Practices

- **Native Audio:** Kling 2.6 supports native audio generation via the `sound` parameter (doubles credit cost).
- **Silent Mode:** Default for cost control (~$0.049/sec vs ~$0.098/sec with audio). Use when text overlays carry the message.
- **Sound Effects:** Specify ambient noise: "classroom sounds", "crowd murmur", "keyboard typing".
- **Dialogue Control:** To have a character speak, use: `Character says: [Exact words]` and include `(no subtitles)` to prevent unwanted on-screen text.
- **Layering:** Describe sounds in sequence: "door opens, footsteps approach, pen clicks".

---

## 5. Iteration and Post-Production

- **Vignette Approach:** Divide longer ads into short, focused scenes or "beats" of 4-8 seconds each.
- **Two Variants:** Generate anchor (straight interpretation) + alternative (different camera/pacing) to enable selection.
- **Expand with AI:** Use Gemini Flash to expand simple ideas into detailed, prompt-ready descriptions (auto-derive mode in the video form).
- **Post-Production:** Text overlays, CTA graphics, and color correction can be added in editing software for brand compliance.

---

## Mapping to Video Session Form

| Framework Element | Simple Mode | Advanced Mode Field |
|---|---|---|
| Scene | Auto-derived from persona + brief | `video_scene` textarea |
| Visual Style | Default: "UGC realistic" | `video_visual_style` input |
| Camera Movement | Default: "handheld" | `video_camera_movement` select |
| Subject & Action | Auto-derived from persona + key message | `video_subject_action` textarea |
| Background/Setting | Auto-derived from persona | `video_setting` input |
| Lighting & Mood | Default: "natural, soft" | `video_lighting_mood` input |
| Audio Cues | `video_audio_mode` toggle (silent/with_audio) | `video_audio_detail` textarea |
| Color Palette | Default: brand colors | `video_color_palette` input |
| Negative Prompt | Default: brand safety | `video_negative_prompt` textarea |
