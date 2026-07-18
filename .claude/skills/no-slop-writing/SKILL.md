---
name: no-slop-writing
description: Write prose that sounds like a sharp human wrote it - concise, concrete, natural voice, zero AI clichés, structured with real delivery methods (BLUF, inverted pyramid, nut graf, SCQA, PEEL, XYZ bullets). Use for ANY prose a person will read or publish - emails, essays, posts, scripts, resume bullets, UI microcopy - and whenever the user asks to write, rewrite, tighten, "humanize," or de-slop text, or complains something "sounds like AI." Also governs DarkeVox's polish pipeline: the distilled prompt rules in polish/prompts.py derive from this skill.
---

# No-Slop Writing

Produce writing that a good writer would be proud to put their name on. Not "professional." Not "polished." Good, meaning a real person with a point of view said something specific in the fewest words that still land.

The single test that catches almost everything: read it aloud in your head. If a sentence is something no actual person would say out loud to a friend they respect, rewrite it until it is. "This project stands as a testament to the power of collaboration" fails the test. "We only pulled this off because six people gave up their weekends" passes.

## Workflow

Write in passes. Drafting and de-slopping at the same time produces mush.

### 1. Find the point before writing anything

Every piece has one job: the thing the reader should know, feel, or do at the end. State it to yourself in one plain sentence. If you can't, you're not ready to write. Also decide:

- Who's reading this? A teacher, a stranger on the internet, a professor you're cold-emailing. Voice follows audience.
- Whose voice is it? If it goes out under the user's name, sound like them: their age, their register, their vocabulary. A 16-year-old's blog post should not contain "paradigm." Steal phrasing from how the user talks in the conversation.
- How short can it be? Decide a target length, then aim under it. Nobody has ever complained that good writing ended too soon.

### 2. Pick the delivery structure

Different jobs move information differently. Before drafting, read `references/delivery-methods.md` and choose the structure that fits: BLUF for emails and requests, inverted pyramid for news and announcements, anecdotal lede plus nut graf for features and blog posts, SCQA for proposals and pitches, PEEL for analytical essay paragraphs, the XYZ formula for resume and activity bullets, and the ladder of abstraction whenever the topic is an abstract idea.

Structure is a decision, not a default. The wrong one (an essay written like a news brief, an email written like a feature) reads as off even when every sentence is clean.

### 3. Draft for the point, not the format

Lead with the most interesting true thing: a specific fact, a scene, a claim. Never with throat-clearing ("In today's world...", "When it comes to...", a rhetorical question). Make every paragraph earn the next one. Stop when the point has landed. Do not write a conclusion that summarizes what the reader just read; if the piece needs an ending, end on a specific image, a consequence, or the sharpest line you've got.

### 4. Slop hunt

Read `references/banned-patterns.md` and sweep the draft against it. This is not optional and not a skim. The patterns in that file are the exact tells readers, teachers, and editors now spot instantly. Every hit gets rewritten, not just deleted, because slop usually marks a spot where the draft was vague. Replace it with something specific.

### 5. Rhythm pass

Human prose has uneven texture. Check for:

- Sentence length variance. If three sentences in a row have similar length and shape, break one. Short sentences hit hard. Then let a longer one stretch out and carry the detail that actually needs room.
- Paragraph variance. Paragraphs should not all be 3 to 4 sentences. A one-line paragraph is legal and powerful.
- Repeated openers. Two sentences in a paragraph starting with the same word, or every paragraph opening with a transition ("However," "Additionally," "Moreover"): fix it. Most transitions can just be cut. If the ideas are in the right order, the reader doesn't need a tour guide.

### 6. The editor pass

Reread the whole piece as a hostile, specific reader: a newspaper editor with a red pen, or an English teacher who has read forty AI essays this semester and is looking for the forty-first. Go sentence by sentence and ask: would this person circle anything? Anything they'd circle gets rewritten. This pass catches what the checklists miss, because editors react to the overall feel (too smooth, too balanced, weirdly confident about nothing) and not just individual phrases.

Then cut 10%. A finished draft can always lose another 10%, usually adjectives, qualifiers ("very," "quite," "rather," "arguably"), and sentences that restate the previous sentence in different words.

## The rules that do the most work

Full principles with before/after examples are in `references/craft.md`. Read it when writing anything longer than a paragraph. The short version:

1. Concrete beats abstract. One real example outperforms three abstract claims. "Cut costs" is dead; "cut the AWS bill from $340 to $90 a month" is alive.
2. Verbs carry sentences. "Made a decision" becomes "decided." "Is indicative of" becomes "shows." Hunt nominalizations (-tion, -ment, -ance words doing a verb's job).
3. Take a position. Say the thing. "Some might argue X, while others contend Y" is a way of saying nothing. Commit, then defend it.
4. Earn every adjective. "Innovative," "compelling," "vibrant" are claims with no evidence. Either show the evidence or cut the word.
5. One idea per sentence. If a sentence needs two comma clauses and a parenthetical to hold together, it's two sentences.
6. No em dashes. They are now the single most recognized AI tell. Rewrite with a period, a comma, a colon, or parentheses. Details in the banned-patterns file.
7. Prose means prose. No bullet lists, no bolded-term-colon patterns, no headers in an essay or blog post unless the user asks. Ideas connect in sentences.
8. Don't mirror the prompt. If asked for "the causes and effects of X," don't write a Causes section and an Effects section. Find the actual structure of the idea.
9. Imperfect is human. Contractions, a sentence fragment for emphasis, starting with "And" or "But": all fine. Grammatical perfection with zero personality is its own tell.

## Two failure modes to avoid

**Overcorrecting into fake-casual.** "Look, here's the thing" and "Let's be real" are just a different flavor of slop. Forced slang, performed edginess, and self-aware "I'm being so human right now" energy read worse than the clichés they replace. The target is natural, not casual. The register can be formal (a cold email to a professor should be), but every sentence still has to be one a person would actually write.

**Sanding off all confidence.** Deleting hedges doesn't mean adding hype. If something is genuinely uncertain, say so once, plainly ("I'm not sure this scales past 50 users"), instead of wrapping every claim in "may potentially help to."

## Output habits

- Deliver the writing itself, not a lecture about the writing. Skip preambles like "Here's a draft that avoids clichés."
- For anything the user will publish or submit, offer one round of "want it tighter/looser/more formal?" rather than three unprompted variants.
- When editing someone's existing text, preserve their voice and their good lines. The job is removing slop, not replacing their style with a house style.
