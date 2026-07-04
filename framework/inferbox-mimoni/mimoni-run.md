---
description: Autonomní one-shot orchestrace "popis úkolu -> draft PR" (mimoni). Git worktree izolace, TDD, validační fix-loop, draft PR.
argument-hint: "<popis úkolu>"
---

# Mimoni Run — inferbox

Spusť neobsluhovaný one-shot běh: popis úkolu dovnitř → draft PR ven, bez zásahu člověka mezi tím.
Deterministické kroky (git, lint, test) běží jako shell příkazy s kontrolou exit kódu. Agentní kroky
(plánování, implementace, oprava) provádíš ty s akumulovaným kontextem. Stav sleduješ v `.mimoni/`.

**Task description:** `$1` (a `$ARGUMENTS` pokud víc slov)

## Variables

- `PROJECT_ROOT` = aktuální adresář projektu (`pwd`)
- `BLUEPRINT_DIR` = `$CLAUDE_PROJECT_DIR/.claude/mimoni/blueprints/`
- `CONFIG` = `$CLAUDE_PROJECT_DIR/mimoni.yaml`

## Instructions

- Nikdy nesahej na `.env` (hook to blokuje). Nikdy nepushuj rozbitý kód.
- Draft PR vždy, když `pr.draft: true`. Člověk reviewuje před merge.
- Selhání deterministického kroku mimo fix-loop = okamžitý halt, run status `failed`.

## Workflow

### 1. Načti a zvaliduj config
```bash
test -f mimoni.yaml || { echo "mimoni.yaml nenalezen"; exit 1; }
uv run --with pyyaml python -c "import yaml; c=yaml.safe_load(open('mimoni.yaml')); print('config OK')"
```
Ověř povinná pole: `blueprint`, `validation.{lint,typecheck,test}`, `pr.{branch_prefix,max_retries}`.
Když chybí → nahlaš které a zastav.

**PRECONDITION check** — ověř, že validační příkazy vůbec běží (env nainstalován):
```bash
cd backend && uv run ruff check . --version >/dev/null 2>&1 || echo "VAROVÁNÍ: backend env není připraven (uv sync, Python 3.12)"
```
Když env není připraven, nahlaš uživateli a zastav — mimoni bez zelené validace nemá smysl.

### 2. Vyber a načti blueprint
Přečti `blueprint` z configu (`standard`/`bugfix`/`test`/`migration`). Načti
`$BLUEPRINT_DIR/<blueprint>.md`. Když neexistuje → nahlaš dostupné a zastav.

### 3. Zaznamenej PROJECT_ROOT a fetchni default branch
```bash
PROJECT_ROOT=$(pwd)
default_branch=$(git symbolic-ref refs/remotes/origin/HEAD | sed 's@^refs/remotes/origin/@@')
git fetch origin "$default_branch"
```

### 4. Vygeneruj run ID a vytvoř worktree (izolace)
```bash
timestamp=$(date +%Y%m%d-%H%M%S)
slug=$(echo "$ARGUMENTS" | tr '[:upper:]' '[:lower:]' | tr -cs '[:alnum:]' '-' | sed 's/^-//;s/-$//' | cut -d'-' -f1-5)
random4=$(head -c 4 /dev/urandom | xxd -p | head -c 4)
run_id="${timestamp}-${slug}-${random4}"
git worktree add "/tmp/mimoni-${run_id}" -b "mimoni/${run_id}" "origin/${default_branch}"
cd "/tmp/mimoni-${run_id}"
```
Selhání worktree = halt.

### 5. Inicializuj state file
Vytvoř `${PROJECT_ROOT}/.mimoni/${run_id}.yaml` (do PŮVODNÍHO projektu, ne worktree) se schématem:
`run_id, task, blueprint, branch, status: running, started_at, current_step, steps[], pr_url: null`.
Naplň `steps` z nadpisů blueprintu (typ `[agent]`/`[deterministic]`).

### 6. Proveď kroky blueprintu (uvnitř worktree)
Sekvenčně. Před každým krokem aktualizuj state (`running`, `current_step`).
- `[deterministic]`: spusť příkaz(y), zkontroluj exit kód. 0 → `completed`. Nenulový: pokud je to
  Local Validation → fix-loop (krok 7); jinak `failed` + halt.
- `[agent]`: proveď popsanou práci (plán/kód/fix) s kontextem z `rule_files` a předchozích kroků.
Substituuj `${config.validation.lint}` atd. hodnotami z `mimoni.yaml`.

### 7. Fix/retry loop (max `pr.max_retries`, default 2)
Při selhání Local Validation: diagnostikuj z výstupu → cílená oprava → re-validace všech tří příkazů.
Vše zelené → ven z loopu. Po vyčerpání retries: state `failed`, NEpushuj, ukliď worktree
(`git worktree remove --force`), nahlaš a zastav.

### 8. Commit, push, úklid worktree
```bash
git add -A
git commit -m "mimoni: <stručný souhrn>"
git push -u origin "mimoni/${run_id}"
cd "${PROJECT_ROOT}" && git worktree remove "/tmp/mimoni-${run_id}"
```

### 9. Vytvoř draft PR
```bash
cd "${PROJECT_ROOT}"
gh pr create --head "mimoni/${run_id}" --title "<souhrn>" \
  --body "<co, proč, přístup, výsledky validace, blueprint>" \
  --base "${default_branch}" --draft --label "mimoni" --reviewer "masserfx"
```
Zachyť PR URL, aktualizuj state (`pr_url`, `status: completed`, `completed_at`).

### 10. Report
Success: task, blueprint, branch, PR URL, validace (lint/typecheck/test ✓), state file cesta.
Failure: krok kde selhal, chyba, branch (zachován), state file cesta.
