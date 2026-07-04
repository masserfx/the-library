---
name: inferbox-pi-team
description: Šablony Pi multi-team agentů pro nový tenant — Orchestrator/Leads/Members se strukturálním domain sandboxem. SaaS jádro inferbox orchestration frameworku.
---

# inferbox-pi-team

Startovní sada pro postavení Pi multi-team orchestrace nad novým projektem (tenant). Postaveno na Pi coding agent (pi.dev).

## Co obsahuje

`agents/` — referenční šablony agentů (odvozené z inferbox implementace):
- `orchestrator.md` — jediné rozhraní pro uživatele, routuje na týmy
- `engineering-lead.md`, `validation-lead.md` — vedoucí týmů (delegate)
- `backend-dev.md`, `frontend-dev.md` — workeři
- `security-reviewer.md` — read-only security recenzent

## Jak vytvořit config pro nový tenant

1. Zkopíruj `agents/` do `<tenant-repo>/.pi/<tenant>/agents/`.
2. **Uprav specifika**: v tělech agentů nahraď doménové zmínky (inferbox, Infer s.r.o., Pohoda, strojírna) za doménu nového tenanta. Uprav stack v instrukcích.
3. **Domain scoping** (klíčový bezpečnostní prvek): v `domain:` každého workera nastav úzké cesty (jen jeho část repa, `delete: false` mimo ni). Leads a security-reviewer read-only + zápis jen do `.pi/`.
4. **Model tiering** (cost): opus na orchestrator + složité agenty, sonnet na jádro/security, gemini-flash/haiku na levnější mechanickou práci. Model v team-config YAML `model:` má přednost před frontmatterem.
5. Vytvoř `<tenant>-config.yaml` s hierarchií (viz níže).
6. Spusť: `teams --team .pi/<tenant>/<tenant>-config.yaml`.

## Šablona team-config.yaml

```yaml
---
orchestrator: { name: Orchestrator, path: .pi/<tenant>/agents/orchestrator.md, color: "#72f1b8" }
paths: { agents: .pi/<tenant>/agents/, sessions: .pi/<tenant>/sessions/ }
shared_context: [README.md, CLAUDE.md]
teams:
  - team-name: Engineering
    consult-when: Staví a mění kód.
    lead: { name: Engineering Lead, path: .pi/<tenant>/agents/engineering-lead.md, color: "#ff6e96" }
    members:
      - { name: Backend Dev, path: .pi/<tenant>/agents/backend-dev.md, color: "#ff7edb", consult-when: API, DB, business logika }
      - { name: Frontend Dev, path: .pi/<tenant>/agents/frontend-dev.md, color: "#36f9f6", consult-when: UI, klient }
  - team-name: Validation
    consult-when: Validuje práci. Testy, security.
    lead: { name: Validation Lead, path: .pi/<tenant>/agents/validation-lead.md, color: "#ff9e64" }
    members:
      - { name: Security Reviewer, path: .pi/<tenant>/agents/security-reviewer.md, color: "#f7768e", consult-when: threat model, OWASP }
```

## Reference

Kompletní funkční implementace (9 agentů, 2 configy, expertise, skills) je v `infer-forge/.pi/inferbox/` jako vzor.

## Bezpečnost

NEPOUŽÍVAT `refresh-anthropic-key.sh` trik (Max OAuth do Pi) — porušení Anthropic ToS. Jen API klíče nebo OpenRouter.

Vyžaduje: Pi coding agent (`npm i -g @mariozechner/pi-coding-agent`), bun, `teams` alias z lead-agents.
