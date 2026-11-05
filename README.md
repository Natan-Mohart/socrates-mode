# Socrates Mode

**A Claude skill that asks before it answers and proves every claim.**

Most AI answers fail in two places: they answer the question you typed instead of the problem you have, and they sound confident even when nothing stands behind the claim. Socrates Mode fixes both.

## How it works

You ask → Claude asks back → You answer → Research → Proof

1. **Question.** Before answering, Claude asks 1 to 3 questions about your goal, your context and the premise of your question. Reply `go` to skip and use its stated defaults.
2. **Research.** It searches for evidence for and against its first idea and ranks it: meta-analyses > RCTs > cohort studies > expert opinion > blogs. It opens every source and checks year, sample size, funding, retractions and whether the study fits you.
3. **Prove.** Every sourced claim comes with an exact quote from the page. Then a script, not the model, checks the sources (see below). Tags come from that result:
   - `[VERIFIED]` the checker found the quote on the live page
   - `[UNCHECKED]` quote and link given, but the page could not be reached by code (paywall, bot block, network off)
   - `[SNIPPET]` only a search snippet or abstract was seen
   - `[MEMORY]` known but not sourced now, verify it yourself
   - `[WEAK]` thin, old or conflicting evidence
4. **Challenge.** Every answer ends with the strongest counterargument, what would change its mind, what you should double-check, and one question to think about.
5. **Audit.** Before sending, it checks that no number, study or link is unsourced.

When you ask it to build something (a plan, a routine, a strategy), it builds it from the evidence, ties each part to your answers, and adds technique videos for physical exercises.

## The source checker: the model doesn't grade its own homework

A label like `[VERIFIED]` is worthless if the model can just claim it opened a page. So the skill ships with [`scripts/verify_sources.py`](socrates-mode/scripts/verify_sources.py), a small standard-library Python script. Claude runs it as a visible step in the chat. For every source it:

1. downloads the page itself,
2. checks the page opens (dead links and invented domains fail),
3. searches the page for the exact quote Claude gave.

It prints a table: `PASS`, `PARTIAL`, `FAIL` or `UNCHECKED`. Only `PASS` becomes `[VERIFIED]`. A failed source is never shown as verified. Run `/socrates recheck` at any time to repeat the check.

You can also run it yourself on any list of claims:

```
python3 verify_sources.py sources.json
```

## Install (claude.ai)

1. Download [`socrates-mode.zip`](https://github.com/Natan-Mohart/socrates-mode/raw/main/socrates-mode.zip).
2. Go to **Settings → Capabilities** and turn on **Create and edit files** and **Allow network egress** (the checker needs internet access to open the pages).
3. Go to **Customize → Skills → Add → Upload skills** and choose the ZIP.
4. Type `/socrates` in any chat.

Menu names can differ slightly between app versions. Skills are private to your account.

## Commands

| Command | What it does |
|---|---|
| `/socrates` | Full mode: questions first, then research and a proven answer |
| `/socrates fast` | Skip the questions, state assumptions, then research |
| `/socrates check` | Paste any text or AI answer and fact-check it claim by claim |
| `/socrates recheck` | Run the source checker again on every source in the chat |
| `exit socrates` | Back to normal mode |

## Example

```
/socrates Find the latest meta-analyses on muscle growth,
then build me a training plan based on them.
```

Claude asks about training experience, schedule and injuries first, then returns a day-by-day plan where every rule is tagged and linked to the study behind it.

## Honest limits

- It works best with web search turned on. Without search, it tags everything as `[MEMORY]`.
- The checker proves a quote exists on a live page. It cannot prove the model understood that page correctly. The quote and link are there so you can judge that in seconds.
- Some sites block automated access or sit behind paywalls. Those sources stay `[UNCHECKED]`, never `[VERIFIED]`.
- Tags make the evidence visible and checkable. They do not make Claude infallible. Check what matters.
- This is a community skill, not an official Anthropic feature.

## License

MIT
