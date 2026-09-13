-- Seed: the Harada board — 8 themes, 64 actions. Ported from docs/harada-board.html.
-- Re-runnable: ON CONFLICT updates definitions in place, so edit here and re-apply.
--
-- Measurability audit (text-only tutor, Phase 1 data):
--   40 cells score automatically from existing tables; 24 are 'manual' because
--   the honest measurement needs voice, human grading, or data we don't log yet.
--   A manual cell never flips to done on its own — the learner toggles it.
-- metric_args contracts are documented in app/harada_metrics.py.

BEGIN;

INSERT INTO harada_themes (id, slug, name_en, name_el) VALUES
(0, 'pronunciation', 'Pronunciation & Script', 'Προφορά & Αλφάβητο'),
(1, 'vocabulary',    'Vocabulary & SRS',       'Λεξιλόγιο'),
(2, 'grammar',       'Grammar & Morphology',   'Γραμματική'),
(3, 'listening',     'Listening',              'Ακρόαση'),
(4, 'speaking',      'Speaking',               'Ομιλία'),
(5, 'reading',       'Reading',                'Ανάγνωση'),
(6, 'writing',       'Writing',                'Γραφή'),
(7, 'habit',         'Habit & Environment',    'Συνήθεια & Περιβάλλον')
ON CONFLICT (id) DO UPDATE SET
  slug = EXCLUDED.slug, name_en = EXCLUDED.name_en, name_el = EXCLUDED.name_el;

INSERT INTO harada_actions (theme_id, slot, label, measure, metric_kind, metric_args) VALUES
-- 0 · Pronunciation & Script
(0, 0, 'Write all 24 letters from memory, upper and lower case',
       'Lesson A1-1 scored ≥0.9', 'lesson_score', '{"level":"A1","seqs":[1],"min":0.9}'),
(0, 1, 'Final sigma ς vs σ — 20 words with zero slips',
       'No final-sigma error pattern in the last 5 sessions', 'error_absent', '{"patterns":["sigma"],"sessions":5}'),
(0, 2, 'Drill the vowel digraphs αι ει οι ου',
       'Lesson A1-1 scored ≥0.9', 'lesson_score', '{"level":"A1","seqs":[1],"min":0.9}'),
(0, 3, 'Drill the clusters μπ ντ γκ τζ in initial and medial position',
       'Tutor pronunciation check — needs voice; self-assessed for now', 'manual', '{}'),
(0, 4, 'Place the τόνος correctly on 50 known words',
       'No stress/accent error pattern in the last 5 sessions', 'error_absent', '{"patterns":["stress","accent","tonos","τόνος"],"sessions":5}'),
(0, 5, 'Shadow 5 minutes of native audio every day',
       'Routine check "shadow_5" on 6 of the last 7 days', 'routine_days', '{"key":"shadow_5","days":6,"window":7}'),
(0, 6, 'Record yourself reading a paragraph; compare against a native read',
       'Monthly recording, self-scored', 'manual', '{}'),
(0, 7, 'Hear the difference: δ/θ, and γ before ε/ι vs α/ο/ου',
       'Minimal-pair listening drill — needs audio; self-assessed', 'manual', '{}'),
-- 1 · Vocabulary & SRS
(1, 0, 'Clear the SRS due queue every day — zero overdue',
       'Routine check "srs_cleared" on 7 of the last 7 days', 'routine_days', '{"key":"srs_cleared","days":7,"window":7}'),
(1, 1, 'Take on 10 new words per tutor session',
       'Average ≥10 words introduced per session over the last 5 sessions', 'session_metric', '{"field":"new_words","min":10,"sessions":5}'),
(1, 2, '500 words held at ≥80% recall',
       '500 SRS rows at ≥0.8 recall, each seen at least twice', 'vocab_count', '{"n":500,"recall":0.8}'),
(1, 3, '1,500 words held at ≥80% recall',
       '1,500 SRS rows at ≥0.8 recall, each seen at least twice', 'vocab_count', '{"n":1500,"recall":0.8}'),
(1, 4, 'Learn every noun with its article — never bare',
       'Self-assessed until vocab items carry part-of-speech', 'manual', '{}'),
(1, 5, 'Learn every verb as 1st person singular, and be able to conjugate it',
       'Self-assessed until conjugation drills are tracked', 'manual', '{}'),
(1, 6, 'Build 8 topic clusters: café, market, travel, home, work, health, weather, family',
       '≥40 words at ≥0.8 recall tagged with each of the 8 clusters', 'vocab_recall', '{"tags":["cafe","market","travel","home","work","health","weather","family"],"n":40,"recall":0.8}'),
(1, 7, 'Weekly leech review — re-teach anything failed 3 or more times',
       'Routine check "leech_review" once in the last 7 days', 'routine_days', '{"key":"leech_review","days":1,"window":7}'),
-- 2 · Grammar & Morphology
(2, 0, 'Conjugate είμαι and έχω with no hesitation',
       'Lessons A1-3 and A1-7 scored ≥0.9', 'lesson_score', '{"level":"A1","seqs":[3,7],"min":0.9}'),
(2, 1, 'Conjugate -ω and -άω verbs in the present',
       'Lessons A1-9 and A1-16 scored ≥0.9', 'lesson_score', '{"level":"A1","seqs":[9,16],"min":0.9}'),
(2, 2, 'Nominative, accusative and genitive of ο / η / το plus noun',
       'Lessons A1-5, A1-13, A1-21 scored ≥0.85', 'lesson_score', '{"level":"A1","seqs":[5,13,21],"min":0.85}'),
(2, 3, 'Predict gender from the ending: -ος -α -η -ι -ο -μα',
       'No gender-agreement error pattern in the last 5 sessions', 'error_absent', '{"patterns":["gender"],"sessions":5}'),
(2, 4, 'Negate with δεν and μην; ask questions by intonation',
       'Lesson A1-9 scored ≥0.85', 'lesson_score', '{"level":"A1","seqs":[9],"min":0.85}'),
(2, 5, 'Future with θα, subjunctive with να',
       'Lesson A1-19 scored ≥0.85', 'lesson_score', '{"level":"A1","seqs":[19],"min":0.85}'),
(2, 6, 'Aorist of the 30 most common verbs',
       'A2 gate — self-assessed until A2 lessons exist', 'manual', '{}'),
(2, 7, 'Clitic pronoun order — μου το έδωσε, not έδωσε μου το',
       'B1 marker — self-assessed; an absent error at A1 proves nothing', 'manual', '{}'),
-- 3 · Listening
(3, 0, '10 minutes of Greek audio daily, first pass with no subtitles',
       'Routine check "listening_10" on 6 of the last 7 days', 'routine_days', '{"key":"listening_10","days":6,"window":7}'),
(3, 1, 'Greek radio or a podcast during the commute, 3× a week',
       'Routine check "radio" on 3 of the last 7 days', 'routine_days', '{"key":"radio","days":3,"window":7}'),
(3, 2, 'One episode of a Greek series per week, Greek subtitles',
       'Routine check "episode" once in the last 7 days', 'routine_days', '{"key":"episode","days":1,"window":7}'),
(3, 3, 'Transcribe 60 seconds of native speech verbatim',
       'Written submission graded by tutor — self-assessed for now', 'manual', '{}'),
(3, 4, 'Numbers and prices dictation — hear 20, write 20',
       'Lesson A1-15 scored ≥0.9', 'lesson_score', '{"level":"A1","seqs":[15],"min":0.9}'),
(3, 5, 'Get the gist of a 2-minute news bulletin',
       'Tutor comprehension check — needs audio; self-assessed', 'manual', '{}'),
(3, 6, 'Run whole tutor sessions with no English fallback',
       'Your turns in the last 5 sessions contain no English words', 'session_metric', '{"field":"greek_only","min":1,"sessions":5}'),
(3, 7, 'Catch fast-speech contractions: στο, στη, σ'' αυτό, π'' το',
       'Lesson A1-14 scored ≥0.85', 'lesson_score', '{"level":"A1","seqs":[14],"min":0.85}'),
-- 4 · Speaking
(4, 0, '15 minutes of unscripted talking per session',
       'Average ≥15 minutes per session over the last 5 sessions', 'session_metric', '{"field":"minutes_used","min":15,"sessions":5}'),
(4, 1, 'Narrate your day out loud, in the past tense',
       'Lesson A1-22 scored ≥0.85', 'lesson_score', '{"level":"A1","seqs":[22],"min":0.85}'),
(4, 2, 'Order food, shop, and ask directions unprompted',
       'Lessons A1-8, A1-14, A1-15 scored ≥0.85', 'lesson_score', '{"level":"A1","seqs":[8,14,15],"min":0.85}'),
(4, 3, 'Describe a photo for 90 seconds without stopping',
       'Timed drill — needs voice; self-assessed', 'manual', '{}'),
(4, 4, 'One conversation a week with a native speaker or partner',
       'Routine check "native_convo" once in the last 7 days', 'routine_days', '{"key":"native_convo","days":1,"window":7}'),
(4, 5, 'Drive English filler words to zero in a session',
       'Your turns in the last 5 sessions contain no English words', 'session_metric', '{"field":"greek_only","min":1,"sessions":5}'),
(4, 6, 'Catch and fix your own gender agreement mid-sentence',
       'Self-corrections are not logged yet — self-assessed', 'manual', '{}'),
(4, 7, 'Hold a 10-minute conversation on a topic you did not prepare',
       'THE GOAL — the final exit check is always a human judgement', 'manual', '{}'),
-- 5 · Reading
(5, 0, 'Read every sign, menu and label you meet, out loud',
       'Routine check "signs_aloud" on 6 of the last 7 days', 'routine_days', '{"key":"signs_aloud","days":6,"window":7}'),
(5, 1, 'Finish one A1 graded reader cover to cover',
       'Logged completion', 'manual', '{}'),
(5, 2, 'Read one set of Greek news headlines daily',
       'Routine check "headlines" on 6 of the last 7 days', 'routine_days', '{"key":"headlines","days":6,"window":7}'),
(5, 3, 'Read a Greek children''s book start to finish',
       'Logged completion', 'manual', '{}'),
(5, 4, 'Read aloud 5 minutes a day for fluency, not comprehension',
       'Routine check "read_aloud_5" on 6 of the last 7 days', 'routine_days', '{"key":"read_aloud_5","days":6,"window":7}'),
(5, 5, 'Pull 10 unknown words out of every text into the SRS',
       'Word sources are not tracked yet — self-assessed', 'manual', '{}'),
(5, 6, 'Watch with Greek subtitles, not English',
       'Routine check "greek_subs" once in the last 7 days', 'routine_days', '{"key":"greek_subs","days":1,"window":7}'),
(5, 7, 'Read an A2 short story with fewer than 10 lookups',
       'A2 gate — logged completion', 'manual', '{}'),
-- 6 · Writing
(6, 0, 'Three sentences about your day, every day',
       'Routine check "three_sentences" on 6 of the last 7 days', 'routine_days', '{"key":"three_sentences","days":6,"window":7}'),
(6, 1, 'Write out a café order and a shopping list in Greek',
       'Lessons A1-8 and A1-15 scored ≥0.85', 'lesson_score', '{"level":"A1","seqs":[8,15],"min":0.85}'),
(6, 2, 'Learn the Greek keyboard layout, accents included',
       'Your turns in the last 3 sessions are entirely Greek script', 'session_metric', '{"field":"greek_only","min":1,"sessions":3}'),
(6, 3, 'Write 100 words about yourself',
       'Tutor-graded — self-assessed until writing tasks are tracked', 'manual', '{}'),
(6, 4, 'Send a real message to a real Greek speaker',
       'Logged once', 'manual', '{}'),
(6, 5, 'Rewrite five tutor-flagged errors correctly each session',
       'Not tracked per session yet — self-assessed', 'manual', '{}'),
(6, 6, 'Keep one Greek-only line in your daily journal',
       'Routine check "journal_line" on 6 of the last 7 days', 'routine_days', '{"key":"journal_line","days":6,"window":7}'),
(6, 7, 'Write a 200-word narrative in the past tense',
       'A2 gate — self-assessed', 'manual', '{}'),
-- 7 · Habit & Environment
(7, 0, '45 minutes a day, in the same time block',
       '≥45 AI minutes logged on each of the last 7 days', 'session_metric', '{"field":"daily_minutes","min":45,"days":7}'),
(7, 1, 'Never miss two days in a row',
       'No two consecutive inactive days in the last 30 days', 'session_metric', '{"field":"no_double_gap","days":30}'),
(7, 2, 'Switch your phone and OS language to Greek',
       'One-time, then permanent', 'manual', '{}'),
(7, 3, 'Review the session error patterns every week',
       'Routine check "weekly_review" once in the last 7 days', 'routine_days', '{"key":"weekly_review","days":1,"window":7}'),
(7, 4, 'Keep one 90-day target visible; reset it every quarter',
       'Self-assessed — the cycle field on the board', 'manual', '{}'),
(7, 5, 'A Greek music playlist running in the background',
       'Routine check "playlist" on 5 of the last 7 days', 'routine_days', '{"key":"playlist","days":5,"window":7}'),
(7, 6, 'Label 20 things around the house with Greek sticky notes',
       'One-time, 20 labels', 'manual', '{}'),
(7, 7, 'Record a monthly self-assessment and compare it to last month',
       '12 recordings a year — the ground truth against the metric layer', 'manual', '{}')
ON CONFLICT (theme_id, slot) DO UPDATE SET
  label = EXCLUDED.label, measure = EXCLUDED.measure,
  metric_kind = EXCLUDED.metric_kind, metric_args = EXCLUDED.metric_args;

-- Which theme(s) each A1 lesson serves (0 pron, 1 vocab, 2 grammar, 3 listen,
-- 4 speak, 5 read, 6 write, 7 habit). Used for theme rollups on the board.
UPDATE lessons SET theme_ids = v.themes::smallint[]
FROM (VALUES
  (1,'{0}'),  (2,'{4}'),   (3,'{2}'),   (4,'{1,3}'), (5,'{2}'),   (6,'{1,2}'),
  (7,'{2,1}'),(8,'{4,1}'), (9,'{2}'),   (10,'{1}'),  (11,'{1,4}'),(12,'{4}'),
  (13,'{2}'), (14,'{3,4}'),(15,'{1,3}'),(16,'{2}'),  (17,'{4}'),  (18,'{2,1}'),
  (19,'{2}'), (20,'{4,1}'),(21,'{2}'),  (22,'{2}'),  (23,'{1}'),  (24,'{4}')
) AS v(seq, themes)
WHERE lessons.level = 'A1' AND lessons.seq = v.seq;

COMMIT;
