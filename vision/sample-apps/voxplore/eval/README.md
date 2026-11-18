# Evaluation

Measures four things about the system, on the 84 requests in `requests.jsonl`:

- Routing: does the live model call the right tool for a request (image, video, interactive scene, illustrated scene, markup, or no tool)?
- Scene reliability: does a generated scene run in the browser, first time or after the single automatic repair?
- Pixels versus code: for the same request, how many checkable facts does the image model get right, and how many does the generated scene get right?
- Latency per medium.

It also runs the markup tool on three test frames, with the learner's own question, and saves the results and what the tool found for manual review.

## Setup

Uses the same `.env` and credentials as the app, plus a headless browser for the scene check:

```shell
python -m pip install playwright
python -m playwright install chromium
```

To use an installed Chrome instead, set `CHROME_PATH`.

## Run

From the project folder:

```shell
python eval/run_eval.py --limit 2          # quick pass, two requests per category
python eval/run_eval.py                    # full run
python eval/run_eval.py --stages video     # video latency only, 3 videos
python eval/run_eval.py --resume           # continue a run that stopped, keeping what is in results.json
python eval/run_eval.py --resume --stages scenes,compare   # check again the scenes recorded as timed_out
```

Results go to `eval/results/`: `report.md`, `results.json`, each scene's HTML and screenshot, each image, and the marked-up frames. The report is also written to `frontend/results.html`, and the app then shows a Results link in its header.

## How each number is produced

- Routing opens one Live API session per request with the app's own setup message, sends the request as text, and records the first tool call. A request is correct when that tool's medium is in `expected`. The requests in the `ambiguous` category accept more than one medium, and those in `implicit` do not name the medium they need. For markup requests the frame is streamed once per second, as the app does. Requests are typed, not spoken, and each one starts a new session, so follow-up edits are not covered.
- Scene reliability calls the same generator as the app, loads the result in the same sandboxed iframe with the same bridge, and waits a few seconds for script errors. On an error it calls the same repair once. It also counts the clickable parts and the sliders or buttons each scene registers. A scene that does not answer within the time limit in the headless browser, for example because it renders too slowly without a graphics card, is recorded as `timed_out` and the run continues. A later run with `--resume` loads the saved code of each such scene again, without generating it anew, and the report names the scenes checked this way. The scene library is not used, so every scene is generated.
- Pixels versus code sends the image and the scene's screenshot to a judge model (`JUDGE_MODEL`, default `gemini-4-argon`) with the request's `facts`. The verdicts are a model's, so check a sample of the saved files by hand before quoting the numbers. The scene is judged in its initial state only.
- The image prompt in this comparison is the request with a fixed prefix. In the app the live model writes the prompt, so image quality in a real session can differ.

## Editing the request set

One JSON object per line: `id`, `category`, `request`, `expected` (list of accepted media). Scene requests can carry `facts`, which adds them to the pixels versus code comparison. The `hard` category holds scene requests whose facts are counts, values and positions. Markup requests carry `frame` (a JPEG under `eval/`) and `markup` (the marking a correct answer would make, shown in the report next to what the tool found). The three frames here are rendered text; replace them with photos of real handwriting for a fairer test.
