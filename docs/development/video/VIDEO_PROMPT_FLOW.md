# Video (Veo) prompt: how it’s built and how form input gets in

## 1. Where the Veo prompt comes from

The prompt sent to the Veo model is built in **two steps**:

1. **Video spec extraction** (`generate/visual_spec.py`): `extract_video_spec(expanded_brief, campaign_goal, audience, ad_id)` turns the expanded brief (and session/form inputs) into a **VideoSpec** (subject, setting, scene action, pacing, overlays, persona/creative direction, negative prompt, etc.).
2. **Prompt building** (`generate/visual_spec.py`): `build_video_prompt(spec, variant_type)` turns that **VideoSpec** into a single string that is passed to the video API as the **scene description**.

That string is what the Veo client receives (today as `scene_description` on the request object; the current `generate_video` in `generate_video/veo_client.py` is a stub that doesn’t call the real API yet).

---

## 2. How form/session input gets into the video spec

Pipeline flow:

```
Form (New Session)                    Pipeline
─────────────────                    ────────
persona          ──────────────────► brief["persona"] → expand_brief → ExpandedBrief.persona
creative_brief   ──────────────────► brief["creative_brief"] → merged into brief_dict for video
key_message      ──────────────────► brief["key_message"] → (see note below)
video_enabled    ──────────────────► config.video_enabled (gates whether video runs)
video_audio_mode ──────────────────► config.video_audio_mode → brief_dict["video_audio_mode"]
```

- **Persona** comes from the session config (or CLI `--persona`). It’s on the minimal **brief**, then `expand_brief` sets `ExpandedBrief.persona`. When we build the video spec, we use `expanded_brief["persona"]` and map it to **persona-specific video direction** (e.g. `athlete_recruit` → “fast-paced competitive energy, campus/field imagery, urgency pacing”).
- **Creative brief** (e.g. `gap_report`, `ugc_testimonial`, `before_after`) comes from the brief and is merged into the dict passed to `extract_video_spec`. It selects **creative-style direction** (e.g. “data overlay video with score and benchmark numbers animating on screen”).
- **Key message** and **product** are intended to come from the form via the minimal brief. They are used for hook/value-prop/CTA overlay text and defaults. If the expanded-brief dict doesn’t have them at top level, the code falls back to `original_brief` so form-driven key message and product flow through.
- **Video audio mode** (silent / voiceover) is set from session config and written into the brief dict before video spec extraction; it appears in the spec and in the final prompt.

So: **persona, creative_brief, video_audio_mode, and (when wired) key_message/product** are the main form/session knobs that shape the video spec and thus the Veo prompt.

---

## 3. What the final video prompt looks like

`build_video_prompt(spec, variant_type)` produces a string like this (with real values filled in from the spec):

```
Generate a 6-second UGC-style ad video in 9:16. Subject: Parent and high school student. Setting: Home study area with SAT prep materials. Scene action: Parent and high school student working through SAT prep milestones with visible momentum toward outcomes. Persona direction: calm organized before/after score progression with clean transitions. Pacing: fast. Camera: handheld. Audio mode: silent. Text overlay sequence: Raise SAT scores with 1-on-1 tutoring -> Personalized SAT Tutoring -> Learn More. Campaign goal cue: conversion. Style direction: calm organized before/after score progression with clean transitions. Closing CTA overlay: Learn More. Messaging rules: DO [...]; DO NOT [...]. Negative: IMPORTANT: No real brand logos, trademarks, or recognizable brand names visible anywhere in the image. All clothing, equipment, materials, books, devices, and signage must be generic/unbranded. No Nike, Adidas, Under Armour, Apple, Samsung, Wilson, or any other identifiable brand. Use plain/solid colored items instead.
```

For the **alternative** variant, pacing/camera/scene are varied (e.g. “steady” instead of “handheld”, different pacing, “Alternate interpretation with different shot cadence”).

So the **final Veo prompt** is:

- One long paragraph: duration, aspect ratio, subject, setting, scene action (including persona direction), pacing, camera, audio mode, text overlay sequence (hook → value prop → CTA), campaign goal cue, style direction, closing CTA, optional messaging rules, and the **negative** (brand-safety) clause.

---

## 4. Guardrails vs image generation

- **Same brand-safety negative prompt as images**  
  Video uses the same `_BRAND_SAFETY_NEGATIVE_PROMPT` as image generation: no real brand logos/trademarks, no Nike/Adidas/Apple/Samsung/Wilson etc., generic/unbranded clothing and props. It’s set on `VideoSpec.negative_prompt` and appended in `build_video_prompt` as `Negative: {spec.negative_prompt}`.

- **Same brand colors**  
  `VideoSpec` uses `_BRAND_COLORS` (teal, navy, white) from `visual_spec.py`; they’re in the spec and can be reflected in style direction / overlays.

- **Persona and creative direction**  
  Same persona and creative-brief system as images: `_PERSONA_VIDEO_DIRECTION` and `_CREATIVE_VIDEO_DIRECTION` map form choices to video-specific style/pacing/action (e.g. UGC testimonial vs data overlay).

- **Messaging rules from brand KB**  
  If the expanded brief includes `messaging_rules` (from the brand knowledge base), they’re added to the prompt as “DO …; DO NOT …” so video stays within Nerdy’s do’s/don’ts.

- **What’s not in the video prompt**  
  Copy-level compliance (no guarantees, no competitor disparagement, etc.) is enforced in **text** generation and evaluation, not in the video prompt. The video prompt focuses on **visual and pacing** (subject, setting, action, overlays, brand-safe visuals). So: **visual/brand guardrails** = aligned with image generation; **claims/compliance** = handled earlier in the pipeline (brief expansion + ad copy).

---

## 5. Summary

| Question | Answer |
|----------|--------|
| What prompt do we pass to Veo? | The string from `build_video_prompt(spec, variant_type)`: duration, aspect ratio, subject, setting, scene action, pacing, camera, audio, overlay sequence, campaign cue, style direction, CTA, optional messaging rules, and the brand-safety negative. |
| How is it generated from the form? | Form/session set **persona**, **creative_brief**, **key_message**, **video_audio_mode**, etc. Those flow into the **brief** and/or **expanded_brief**; `extract_video_spec` reads them (and `original_brief` for key_message/product when needed) and builds **VideoSpec**; `build_video_prompt` turns VideoSpec into the final prompt. |
| What does the final prompt look like? | One long sentence/paragraph: “Generate a 6-second UGC-style ad video in 9:16. Subject: … Setting: … Scene action: … Pacing: … Camera: … Audio mode: … Text overlay sequence: … Campaign goal cue: … Style direction: … Closing CTA overlay: … [Messaging rules.] Negative: [brand-safety clause].” |
| Guardrails vs image/Nerdy? | Same **brand-safety negative** and **brand colors**; same **persona** and **creative-brief** system; **messaging_rules** from KB included when present. Copy compliance (guarantees, competitors) is handled in text, not in the video prompt. |
