# Conversational Greek in 12 Months — Plan

Oct 16, 2026 · @Ioannis Batsios

&#91;Likely\] At 45 minutes a day you reach A2 by October 2027, not conversational Greek. At 60 minutes a day, speaking first, plus one real Greek speaker each week, you reach the edge of B1. Your tracker can carry the practice, but the build order has to put voice second instead of last, and the teach skill can author the course while the app is built.

## Six problems to fix first

Six things in the current plan will cost you more Greek than any missing feature will.

1. **45 minutes a day does not reach B1.** \[Certain\] 45 minutes × 365 days × 85% of days = 233 hours. \[Likely\] Generic guided-hour estimates put B1 at 350–400 hours, and Greek sits farther from English than the languages those tables usually describe, so it probably needs more. Fix: 60 minutes a day.
2. **The board's own routine adds up to about 85 minutes, not 45.** \[Likely\] Cards (about 15), a 45-minute tutor session, 10 minutes of listening, 5 of reading aloud, three written sentences (5–10) and 5 of shadowing total roughly 85, while cell 7.1 says 45. The card and writing times are my estimates. Fix: one 60-minute block, below.
3. **The roadmap builds speaking last.** \[Certain\] Your requirements trace calls the code today "a writing tutor with a speaking goal attached", and voice is stages 10 and 11, after reading and writing. Fix: pull a thin voice slice forward.
4. **The app cannot hear your accent.** \[Certain\] Speech-to-text returns what it thinks you meant, and stage 11's own primer says an accent that is still intelligible scores well. Fix: targeted drills, plus one human who speaks Greek every week.
5. **Greek shares your evenings with piano, reading, DevOps, SysAdmin, Kubernetes, GLPI and the gym.** \[Certain, from your 2027 list\] Fix: one fixed block, a 20-minute floor day, and no coding inside the block.
6. **Building the app can eat the hours Greek needs.** \[Likely\] Stage 01 has not started, so cycle 1 would run without the app. Fix: start speaking this week with the teach skill and a human; the app is not a prerequisite.

| Level | Guided hours from zero | Source |
| --- | --- | --- |
| A2 | 180–200 | Cambridge guided learning hours, via CEFR |
| B1 | 350–400 | Cambridge guided learning hours, via CEFR |
| B2 | 500–600 | Cambridge guided learning hours, via CEFR |
| Professional working proficiency | 1,100 | US Foreign Service Institute, Category IV (includes Greek) |

The Cambridge figures are generic, not Greek-specific. The FSI figure is for professional proficiency, not conversation.

| Your year | Hours in 12 months |
| --- | --- |
| 45 min/day, 85% of days (the board today) | 233 |
| 60 min/day, 70% of days | 255 |
| 60 min/day, 85% of days | 310 |
| 60 min/day, every day | 365 |

The 85% and 70% adherence rates are my assumptions for real life, not measurements.

## The plan at a glance

The plan is a voice-first daily loop in your tracker, a course folder built with the teach skill, and one weekly conversation with a person.

| Question | Answer |
| --- | --- |
| What | A 60-minute daily block: audio flashcards, a voice session with the tutor, listening, shadowing and three written sentences, started from your tracker's Learning card. |
| Why | Your board's goal: hold a 10-minute unscripted conversation on everyday topics in Greek without switching to English. |
| Who | You; Claude as the daily tutor; a Greek-speaking human tutor once a week; the teach skill as course author. |
| When | Every day in one fixed block, with a 20-minute floor on bad days. Four 90-day cycles from 16 Oct 2026, ending 14 Jan, 14 Apr, 13 Jul and 11 Oct 2027. |
| Where | Tracker home, Learning card, then the greek-tutor app on its own hostname behind Cloudflare Access, on phone or laptop. |
| How | Voice sessions, audio review cards, a weekly human conversation and a monthly recording. The Harada board measures progress; a person grades the real test. |

## A day, a week, a month

The daily block is 60 minutes, and the weekly human conversation replaces that day's voice session, so the average stays at 7 hours a week.

| Min | Step | Where | Cost | Board cells |
| --- | --- | --- | --- | --- |
| 10 | Review due cards: hear the word, say it, then type it | greek-tutor /review | No AI | 1.1 |
| 25 | Voice session with the tutor, speaking first, text as the fallback | greek-tutor /practice | Claude API, speech-to-text, text-to-speech | 4.1 |
| 10 | Listen to real Greek, no subtitles on the first pass | Any source; you log the minutes | No AI | 3.1 |
| 10 | Shadow a native clip, then record yourself and compare | greek-tutor | No AI | 0.6, 0.7 |
| 5 | Write three sentences; the tutor marks them and the errors become cards | greek-tutor | One short Claude call | 6.1 |

- **Floor day, 20 minutes:** the 10-minute card review plus a 10-minute voice mini-session. It keeps cell 7.2 ("never miss two days in a row") alive without a full block.
- **Weekly:** one 30–45 minute conversation with a Greek speaker replaces that day's voice session (cell 4.5). On Sunday, 15 minutes on leeches and the week's errors (cells 1.8 and 7.4).
- **Monthly:** a 3-minute recording on the same prompt each month, played against last month's (cell 7.8).
- **At each cycle close:** a 10-minute unscripted conversation with a person, recorded, which they score on a rubric they fill in. It is the one measurement the app cannot take (cell 4.8).

This changes two board labels: the tutor session goes from 45 to 25 minutes, and cell 7.1 goes from 45 to 60 minutes a day.

## How the tutor should teach

Six changes turn today's text tutor into one that trains speaking, and each is small enough to land in a stage you already have.

1. **Speaking first.** In voice mode, replies run two sentences at most and end with a question you answer aloud. Today's prompt already forces production, but it assumes you type.
2. **Prompt, then recast.** On a repeated error, ask the student to retry before restating the sentence. Today's rule 3 restates the sentence and explains it, which is a recast. The research below favours prompts.
3. **Tell the model it is reading a transcript.** Correct words, not punctuation, and say that accent errors are invisible to it. When what it heard differs from what you meant to say, it asks you to repeat that one word.
4. **Check stress marks in code, not by trust.** \[Likely\] A server-side check can flag any Greek word of two or more syllables that the tutor writes without a tonos, and reject the reply. Modern Greek writes a stress mark on those words.
5. **Validate cards before they enter the deck.** Today the tutor's JSON creates vocabulary cards directly, and the only check is length (app/tutor.py). Require the article on nouns and a stress mark, and check each gloss against a dictionary before it enters spaced repetition. Seed the first 1,500 words from a frequency list, so the deck does not depend on what the model happens to mention.
6. **Ground explanations in the course.** The teach skill's reference sheet for today's lesson goes into the tutor's context, so grammar claims come from sources you vetted rather than from the model's memory.

Greek sounds to drill first, in this order:

| Feature | Why it matters | Drill | Confidence |
| --- | --- | --- | --- |
| Stress | Written as a tonos on every word of two or more syllables, and it changes meaning: πότε (when) vs ποτέ (never) | Say the word, then mark the stress on the typed word | Certain |
| Pure vowels | Greek has five vowel sounds with no glide; English speakers tend to glide | Record 10 words, play them against a native clip | Likely |
| One sound, six spellings | ι η υ ει οι υι all say the same /i/ | Dictation, then spelling correction | Certain |
| γ and χ | Each has two sounds depending on the vowel after it (γ before ε ι sounds like English "y") | Minimal pairs with two voices, then record and compare | Likely |
| Clusters μπ ντ γκ | Sound different at the start of a word and in the middle (cell 0.4) | Read 10 words aloud | Likely |
| θ and δ | English has both sounds ("thin", "this"), so they are easy to make; stage 10 spends a whole drill on them | Short check only | Likely |

## What the research supports

The sources I could open support targeted pronunciation work and prompt-style correction, and are thin on everything else.

| Practice | What the sources show | What it changes in the build | Confidence |
| --- | --- | --- | --- |
| [Corrective feedback](https://www.cambridge.org/core/product/4999EE1C8379B2BF026B148EAF373CA1) | Meta-analysis of 15 classroom studies (N = 827): feedback has significant, durable effects, and prompts (making the learner self-correct) beat recasts (restating the sentence), mostly on free-response tasks | The tutor prompts a retry before it recasts | Certain |
| [Pronunciation teaching](https://experts.nau.edu/en/publications/effects-of-second-language-pronunciation-teaching-revisited-a-pro/) | Review of 77 studies: teaching works best when it targets monitored production of specific sounds, stress or intonation; evidence is weakest for global ratings of spontaneous speech | Short targeted record-and-compare drills, not just more chatting | Certain |
| [Multi-talker listening drills](https://www.cambridge.org/core/product/E38D8F5CE65DC708137B0E95F97C6BC7) | Meta-analysis of 31 studies: small-to-medium production gains (about 10.5% on trained items, 4.5% on untrained) and no strong evidence they last or transfer | Two voices in drills; do not expect them to fix your accent | Certain |
| [Retrieval and spacing](https://www.frontiersin.org/journals/education/articles/10.3389/feduc.2025.1715111/full) | The teach skill builds on both. The one study I opened (8 learners, no control group, internal inconsistencies) is too weak to cite; the wider literature is from memory and unchecked here | Keep spaced repetition; it is cheap and standard | Likely |
| Listening volume | No source opened. Ten minutes a day is the board's number, not a researched one | Log the minutes; revisit at each cycle close | Guessing |
| Talking to people | The teach skill's third pillar, "wisdom", comes from real practitioners, and your board already has cells 4.5 and 6.5. No study opened | A weekly human conversation | Likely |

## Where the teach skill fits

The teach skill is the course author, not the runtime tutor: it builds lessons and reference sheets on your machine, and the app drills them. You run it by hand with `/teach`, in a folder it treats as a workspace for one mission.

| File it keeps | What it holds | What it does here |
| --- | --- | --- |
| MISSION.md | The reason you are learning | Seed it from the board's goal and the cycle-1 target, so the skill does not spend its first session interviewing you |
| RESOURCES.md | Vetted sources, split into knowledge and communities | The missing piece: no vetted grammar, dictionary or community list exists in your repos today, and the skill's rule is never to trust the model's memory |
| lessons/\*.html | One short lesson with an in-browser quiz | One per A1 lesson, starting this week |
| reference/\*.html | Printable cheat sheets | Alphabet and sound chart, stress rules, verb tables; also fed to the tutor as grounding |
| learning-records/\*.md | Misconceptions and prior knowledge | Your Sunday error review adds the non-obvious ones, and they steer the next lesson |

It has no audio and no review scheduling, so spaced repetition and every spoken drill stay in greek-tutor. It allows one mission per workspace, and its learning records hold insights, not session logs.

1. Create `greek-tutor/course/` and write MISSION.md from the board's goal and the 90-day target.
2. Run `claude` in that folder and `/teach` for lesson A1-1, the alphabet and reading basics from `seed/lessons_a1.sql`.
3. In phase 3, greek-tutor serves the lessons and reference sheets read-only at `/learn`, and each lesson links to a button that starts the matching tutor session.
4. In phase 4, the weekly review proposes learning records for you to confirm.

I read the upstream copy (commit 49dd158, 9 Oct 2026) because the skill was not in any of the three folders I can reach. Check that yours matches.

## How the pieces fit

The tracker stays the front door and greek-tutor stays the engine; voice, a course folder and a third hostname are what is new.

Eight decisions shape the build, and each has a recommendation:

| # | Decision | Roadmap default | Recommendation | Why |
| --- | --- | --- | --- | --- |
| 1 | Daily budget | 45 min | 60 min, with a 20-minute floor | The hours table above |
| 2 | How the app reaches Claude | API key; `claude_cli` is opt-in | API key | \[Likely\] `claude_cli` starts one `claude` process per call and returns the whole reply at once (app/llm.py), which is too slow for voice; the API can stream |
| 3 | Tutor model | Haiku 4.5 for turns, Sonnet 4.6 for evaluation | Sonnet 5.5 for turns until stage 13's evals show Haiku matches it | \[Guessing\] a smaller model makes more Greek errors. `.env.example` names `claude-haiku-4-5-20251001` and `claude-sonnet-4-6`; the current IDs are `claude-haiku-5-5` and `claude-sonnet-5-5`, so check the old ones still resolve |
| 4 | Speech-to-text | faster-whisper `small` on CPU | Not `small`: cloud speech-to-text, or `large-v3` on a GPU | \[Certain\] Whisper's Greek error rate on FLEURS is 34% for small, 19% for medium and 11% for large-v3, measured on native speakers, so learners will do worse. Azure lists el-GR for speech-to-text |
| 5 | Text-to-speech | Piper, self-hosted | A cloud neural voice, two voices, cached by text hash | \[Certain\] Piper's only Greek voice is rated low quality: one speaker, 16 kHz, fine-tuned from a low-quality English voice. Google's Chirp 3 HD lists el-GR |
| 6 | Where the app runs | Homelab dev VM | The workstation first, on the `ibatsios_default` network like the tracker | The board mirror is a file the tracker bind-mounts, which works on one Docker host only unless you add a token route (the contract has none). The cost is sharing the single point of failure your stack map already flags |
| 7 | Hostname | Not decided | `greek.ioannisbatsios.com`: a third nginx server block and its own Access app | Mirrors `private.conf`. Microphone capture needs HTTPS, which the tunnel provides |
| 8 | Human tutor | Not in the roadmap | Yes: weekly, 30–45 minutes, conversation and pronunciation | Only a person can grade cells 4.5 and 4.8 |

The tracker's half of the board mirror is not built yet: its Learning card says coming soon, and its plan.md schedules Harada boards as slice 2. Pronunciation scoring is deliberately not decided here; see the gaps section.

## This week

Start speaking before the app exists; only the last two moves below need code.

- [ ] Accept or change the eight recommendations in the decisions table.
- [ ] Put a daily 60-minute block on your calendar so it shows on the tracker's Calendar card.
- [ ] Book a trial lesson with a Greek-speaking conversation tutor.
- [ ] Create `greek-tutor/course/`, write MISSION.md from the board, and run `/teach` for lesson A1-1.
- [ ] Spend 20 minutes on a voice spike: one HTML page using Chrome's built-in speech recognition set to `el-GR`, then read it 10 sentences and see what it writes.
- [ ] Run stage 01 (first real run) on the API backend with current model IDs.

## What I could not verify

Five questions stayed open, and each has a cheap way to settle it.

| Open question | What I found | How to settle it |
| --- | --- | --- |
| Pronunciation scoring for Greek | Azure's pronunciation assessment covers 33 locales, but the table did not load, so I could not confirm el-GR. The open-source OpenPronounce is calibrated only for English | Open Microsoft's language-support page, Pronunciation assessment tab, and look for el-GR |
| Whisper accuracy on learner speech | The error rates I have are for native speakers | Record 10 sentences yourself and read the transcripts |
| Greek voice quality | One forum thread calls ElevenLabs more natural in Greek; I found no measured comparison of Chirp 3 HD, Azure and ElevenLabs, and Azure's Athina and Nestoras voices appear only in third-party listings | Listen to five sentences from each and let your tutor choose |
| Hours to B1 in Greek | The table is generic, not Greek-specific | Treat the cycle-close conversation as the real measurement |
| Voice latency | Not measured | Phase 2 gate: time from the end of your speech to the start of the reply, on your phone |

## Sources

These are the pages I opened, as of 16 Oct 2026.

- [How Long Does It Take to Learn Greek? (noun.town)](https://noun.town/blog/how-long-does-it-take-to-learn-greek/): A2, B1 and B2 hours
- [Foreign Service Institute language difficulty (Atlas & Boots)](https://atlasandboots.com/foreign-service-institute-language-difficulty): Greek in Category IV, 1,100 hours
- [Oral feedback in classroom SLA](https://www.cambridge.org/core/product/4999EE1C8379B2BF026B148EAF373CA1): prompts vs recasts
- [Effects of Second Language Pronunciation Teaching Revisited](https://experts.nau.edu/en/publications/effects-of-second-language-pronunciation-teaching-revisited-a-pro/): 77 studies
- [High variability phonetic training and L2 production (meta-analysis)](https://www.cambridge.org/core/product/E38D8F5CE65DC708137B0E95F97C6BC7): 31 studies
- [Spaced retrieval and fluency (Frontiers in Education)](https://www.frontiersin.org/journals/education/articles/10.3389/feduc.2025.1715111/full): small, weak study
- [The Greek podcast corpus](https://arxiv.org/abs/2406.15284): Whisper error rates on Greek
- [Azure Speech language support](https://learn.microsoft.com/en-my/Azure/ai-services/speech-service/language-support?tabs=pronunciation-assessment): el-GR speech-to-text
- [Chirp 3: HD voices (Google Cloud)](https://docs.cloud.google.com/text-to-speech/docs/chirp3-hd): el-GR listed
- [Piper Greek voice model card](https://huggingface.co/rhasspy/piper-voices/raw/4d68f18217d5c6a4b2418c8c46222d6fcd698acb/el/el_GR/rapunzelina/low/MODEL_CARD): low quality, one speaker
- [OpenPronounce](https://github.com/Halleck45/OpenPronounce): English-only calibration
- [Matt Pocock's skills repo](https://github.com/mattpocock/skills): the teach skill, at skills/productivity/teach
- [Anki forum thread on Greek voices](https://forums.ankiweb.net/t/where-to-get-a-greek-tts-voice-from-that-sounds-natural/60236): user opinions only

Read from your own folders: greek-tutor docs/handoff-items/00-ROADMAP.md and stages 04, 05, 10, 11 and 12, docs/REQUIREMENTS\_TRACE.md, docs/HARADA\_BOARD\_CONTRACT.md, app/llm.py, app/tutor.py, app/claude\_client.py, app/srs.py and .env.example; ibatsios deploy/nginx/private.conf and RUNBOOK.md; tracker docs/plan.md; your Stack Map.
