"""End-to-end Rosetta port of a repo, printing the progress-event stream.

    uv run python scripts/port.py <repo_url_or_path>
    uv run python scripts/port.py                      # defaults to open_deep_research

This is the single orchestration entrypoint (app.pipeline.port_repo) that the
multi-repo tests and the SSE server also use.
"""

import asyncio
import sys

from app.pipeline import port_repo

GOLDEN = "https://github.com/langchain-ai/open_deep_research.git"


async def main(url: str):
    result = None
    async for ev in port_repo(url):
        t, d = ev["type"], ev["data"]
        if t == "phase":
            print(f"\n== {d['phase'].upper()} ==")
        elif t == "framework":
            print(
                f"  framework={d.get('framework')} conf={d.get('confidence')} :: {d.get('summary', '')[:80]}"
            )
        elif t == "repo_tree":
            print(f"  repo: ~{d['loc']} LOC · {d['files']} py files")
        elif t == "analysis":
            g = d["data"] or {}
            keys = list(g)[:4]
            print(f"  [{d['facet']}] keys={keys}")
        elif t == "eval_inputs":
            n = len((d["data"] or {}).get("inputs", []))
            print(f"  eval_inputs: {n} harvested")
        elif t == "mapping":
            print(
                f"  PLAN target={d['target_name']} agents={len(d['agents'])} risks={[r['source'][:40] for r in d['risks']]}"
            )
        elif t == "scaffold":
            print(f"  scaffolded {d['name']}")
        elif t == "file":
            tag = " (patched)" if d.get("patched") else ""
            print(f"    + {d['path']} ({d['loc']} loc){tag}")
        elif t == "repair":
            print(f"  [repair {d['n']}] {len(d['errors'])} error(s)")
        elif t == "verify":
            print(f"  VERIFY ok={d['ok']} repairs={d['repairs']}")
            if not d["ok"]:
                for e in d["errors"]:
                    print("     · " + e[:200])
        elif t == "metrics":
            print(f"  metrics: {d['timings_s']}")
        elif t in ("warning", "error", "declined"):
            print(f"  !! {t}: {d}")
        elif t == "done":
            result = d
            print(
                f"\n== DONE == ok={d['ok']} build_green={d.get('build_green')} repairs={d.get('repairs')} project={d.get('project', '-')}"
            )
    return result


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else GOLDEN
    asyncio.run(main(url))
