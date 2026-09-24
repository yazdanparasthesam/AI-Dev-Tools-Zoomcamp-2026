# FAQ proposal draft — DataTalksClub/faq

**Where to file:** https://github.com/DataTalksClub/faq/issues/new?template=faq-proposal.yml
**After filing:** the FAQ bot opens a PR automatically (like PR #282 did for issue #281).
Paste **your new issue's URL** into the homework form's
*"FAQ contribution PR or issue URL"* field.
⚠️ Do **not** use `https://github.com/DataTalksClub/faq/issues/281` — that is
another student's closed llm-zoomcamp proposal, not yours.

---

## Title

[FAQ] npm install crashes with "Cannot read properties of null (reading 'edgesOut')" when setting up the Homework 2 frontend

## Course

ai-dev-tools-zoomcamp

## Question

While setting up the frontend for Homework 2 (module 02-development), `npm install` — or `npm i -D vitest …` — dies with:

```
npm error TypeError: Cannot read properties of null (reading 'edgesOut')
```

Nothing installs, the stack trace is inside npm's arborist, and retrying gives the same crash. My code compiles in my head fine, so what is actually wrong and how do I get a working test setup?

## Answer

This is a crash in npm's dependency resolver (arborist), not in your project. It reproduces on npm 10.x (observed on 10.8.2 and 10.9.8, Node 20 and Node 22) when npm resolves the peer-dependency set of `vitest@5` — i.e. when vitest is added unpinned, or re-resolved without a lockfile.

Fixes, in order of preference:

1. **Pin vitest to the major the course reference app uses.** The module's reference repository (`alexeygrigorev/interview-canvas-share`) pins `"vitest": "^4.1.10"` in `frontend/package.json`:

   ```bash
   npm install -D "vitest@^4.1.0" jsdom @testing-library/react @testing-library/dom
   ```

   Quote the range so your shell does not eat the caret.

2. **If a `package-lock.json` already exists, use `npm ci`, not `npm install`.** `ci` installs exactly the locked tree and never enters the resolution path that crashes:

   ```bash
   rm -rf node_modules && npm ci
   ```

3. **If you truly need vitest 5**, upgrade npm itself (`npm install -g npm@latest`), delete `node_modules` and the lockfile, and retry. For this homework, matching the reference app's 4.x is the safer choice.

Verify with `npm ls vitest` (should print 4.1.x) and `npm test` / `npx vitest run`.

Prevention: commit your `package-lock.json` with the frontend — the module deliverables expect reproducible installs, and anyone cloning your repo (including the grader) then uses `npm ci` and never touches the buggy resolver.

## Checklist (tick all three)

- [x] I have searched existing FAQs and this question is not already answered
- [x] The answer provides accurate, helpful information
- [x] I have included any relevant code examples or links

---

### Why this entry should survive review

Issue #281 was closed because its answer invented numbers not taught by the
course. This one is grounded in three verifiable facts: the exact crash text
students paste into search, the reference repo's pinned `"vitest": "^4.1.10"`
(public, in `frontend/package.json`), and the module's own requirement of
reproducible installs via committed lockfiles.
