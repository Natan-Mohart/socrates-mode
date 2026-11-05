# Socrates Mode

**A Claude skill that asks before it answers and proves every claim.**

Most AI answers fail in two places: they answer the question you typed instead of the problem you have, and they sound confident even when nothing stands behind the claim. Socrates Mode fixes both.

## How it works

You ask → Claude asks back → You answer → Research → Proof

1. **Question.** Before answering, Claude asks 1 to 3 questions about your goal, your context and the premise of your question. Reply `go` to skip and use its stated defaults.
2. **Research.** It searches for evidence for and against its first idea and ranks it: meta-analyses > RCTs > cohort studies > expert opinion > blogs. It opens every source and checks year, sample size, funding, retractions and whether the study fits you.
3. **Prove.** Every important claim gets a tag:
   - `[VERIFIED]` source opened in this session, with title, year and link
   - `[MEMORY]` known but not checked now, verify it yourself
   - `[WEAK]` thin, old or conflicting evidence
4. **Challenge.** Every answer ends with the strongest counterargument, what would change its mind, what you should double-check, and one question to think about.
5. **Audit.** Before sending, it checks that no number, study or link is unsourced.

When you ask it to build something (a plan, a routine, a strategy), it builds it from the evidence, ties each part to your answers, and adds technique videos for physical exercises.

## Install (claude.ai)

1. Download [`socrates-mode.zip`](https://github.com/Natan-Mohart/socrates-mode/raw/main/socrates-mode.zip).
2. Go to **Settings → Capabilities** and turn on **Create and edit files**.
3. Go to **Customize → Skills → Add → Upload skills** and choose the ZIP.
4. Type `/socrates` in any chat.

Menu names can differ slightly between app versions. Skills are private to your account.

## Commands

| Command | What it does |
|---|---|
| `/socrates` | Full mode: questions first, then research and a proven answer |
| `/socrates fast` | Skip the questions, state assumptions, then research |
| `/socrates check` | Paste any text or AI answer and fact-check it claim by claim |
| `exit socrates` | Back to normal mode |

## Example

```
/socrates Find the latest meta-analyses on muscle growth,
then build me a training plan based on them.
```

Claude asks about training experience, schedule and injuries first, then returns a day-by-day plan where every rule is tagged and linked to the study behind it.

## Honest limits

- It works best with web search turned on. Without search, it tags everything as `[MEMORY]`.
- Tags make the evidence visible. They do not make Claude infallible. Check what matters.
- This is a community skill, not an official Anthropic feature.

## License

MIT
