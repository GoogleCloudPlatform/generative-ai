# Managed Agent deliverable skills

Skill definitions for the Managed Agent (Antigravity) autonomous sandbox:
professional presentation decks (.pptx), business documents (.docx / PDF),
and self-contained HTML reports.

How they are delivered: the generated setup script copies these files from
the fetched agent template into the demo project (skills/...), and
create_managed_agent.py registers that directory as the agent's skills
source. There is no build step - edit the SKILL.md files directly.

Authoring rules:
- Frontmatter: name + description (the description tells the agent when to
  use the skill).
- English and printable ASCII only; the deliverable itself follows the
  task language (each skill states this rule).
- Keep instructions concrete: process, design system, verification,
  delivery. The agent follows them literally.
