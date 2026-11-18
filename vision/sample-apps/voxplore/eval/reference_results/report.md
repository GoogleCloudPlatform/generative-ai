# VoxPlore evaluation

Live model: `gemini-3.8-live`. Image: `gemini-nano-banana-2.1`. Video: `gemini-omni-1.2-flash`. Scene: `gemini-4-argon`. Judge: `gemini-4-argon`.

## Routing

A request counts as correct when the first tool the live model calls is one of the expected media (or no tool when none is expected).

Overall: 78/84 (93%)

| Expected | Correct | none | image | video | scene | illustrated | annotate | edit | other | error |
|---|---|---|---|---|---|---|---|---|---|---|
| none | 10/10 (100%) | 10 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| image | 12/14 (86%) | 0 | 11 | 0 | 0 | 2 | 0 | 0 | 0 | 1 |
| video | 8/8 (100%) | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 0 | 0 |
| scene | 18/18 (100%) | 0 | 0 | 0 | 18 | 0 | 0 | 0 | 0 | 0 |
| ambiguous | 6/6 (100%) | 0 | 2 | 0 | 3 | 1 | 0 | 0 | 0 | 0 |
| hard | 5/6 (83%) | 0 | 1 | 0 | 5 | 0 | 0 | 0 | 0 | 0 |
| implicit | 11/14 (79%) | 4 | 5 | 0 | 4 | 1 | 0 | 0 | 0 | 0 |
| annotate | 3/3 (100%) | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 |
| illustrated | 5/5 (100%) | 0 | 0 | 0 | 0 | 5 | 0 | 0 | 0 | 0 |

Misrouted requests:

- image-06: "Show me what a mitochondrion looks like." expected image, got illustrated
- image-07: "Draw a flowchart of the scientific method." expected image, got error
- hard-04: "Show a regular hexagon and its interior angles." expected scene, got image
- implicit-02: "What does a cheetah look like when it runs?" expected video, got image
- implicit-06: "How does a jellyfish swim?" expected video/image, got none
- implicit-14: "How does a frog's life cycle go?" expected image/video, got none

## Scene reliability

Each scene is generated once, loaded in headless Chrome in the app's sandboxed iframe, and given the app's single automatic repair if it raises a script error.

| Outcome | Scenes |
|---|---|
| ok_first | 22/24 (92%) |
| timed_out | 2/24 (8%) |

Scenes with clickable parts: 22/22 (100%). With sliders or buttons: 22/22 (100%).

Failures:

- scene-12: "Let me explore how a sine wave changes with frequency and amplitude." (timed_out) no answer from the page within 29 seconds
- hard-03: "Plot the line y = 2x + 1 and let me move a point along it." (timed_out) no answer from the page within 29 seconds

## Pixels versus code

The same request rendered by the image model and by a generated scene, each checked by the judge model against the same facts. Judged by a model, so spot-check the saved files.

| Medium | Requests judged | Correct | Incorrect | Not shown |
|---|---|---|---|---|
| Pixels (image model) | 18 | 56/62 (90%) | 4/62 (6%) | 2/62 (3%) |
| Code (scene) | 16 | 55/56 (98%) | 0/56 (0%) | 1/56 (2%) |

On the 16 requests where both were judged:

| Request | Pixels correct | Code correct |
|---|---|---|
| scene-01 | 4/4 | 4/4 |
| scene-02 | 3/3 | 3/3 |
| scene-03 | 3/3 | 3/3 |
| scene-04 | 3/4 | 4/4 |
| scene-05 | 4/4 | 4/4 |
| scene-06 | 4/4 | 4/4 |
| scene-07 | 4/4 | 4/4 |
| scene-08 | 4/4 | 4/4 |
| scene-09 | 3/4 | 4/4 |
| scene-10 | 3/3 | 3/3 |
| scene-11 | 2/3 | 2/3 |
| hard-01 | 3/3 | 3/3 |
| hard-02 | 4/4 | 4/4 |
| hard-04 | 3/3 | 3/3 |
| hard-05 | 3/3 | 3/3 |
| hard-06 | 1/3 | 3/3 |

## Markup on a camera frame

The tool reads the frame, then draws on it. Check by eye: does the finding match the expected mistake, is the right thing marked, and is the frame otherwise unchanged?

- annotate-01: annotate-01_markup.png. Found: In gradient descent, you move in the direction opposite to the gradient to minimize the loss, so you need to subtract instead of add. The correct formula is w = w - lr * dL/dw. Expected: Circle the plus sign and write a minus sign next to it.
- annotate-02: annotate-02_markup.png. Found: The addition is incorrect; 347 + 285 equals 632, not 622. Remember to carry the 1 from the ones column (7 + 5 = 12) into the tens column. Expected: Circle the result 622 and write 632 next to it.
- annotate-03: annotate-03_markup.png. Found: You forgot the middle term when expanding the squared binomial. The correct expansion is (x + 3)^2 = x^2 + 6x + 9. Expected: Circle the right-hand side and write '+ 6x' in the gap between x^2 and 9.

## Latency (seconds)

| Step | Runs | Median | p90 |
|---|---|---|---|
| Live model, request to tool call | 69 | 3.5 | 4.8 |
| Image generation | 18 | 22.9 | 31.4 |
| Scene generation | 24 | 18.8 | 28.6 |
| Scene repair | 0 | | |
| Markup | 3 | 17.8 | 17.9 |
