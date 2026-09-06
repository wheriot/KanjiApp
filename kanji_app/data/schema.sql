-- Kanji App database schema.
--
-- Applied by kanji_app.data.db.migrate(). The whole schema is defined up front
-- (polymorphic cards, a real deck table) even though early phases only exercise
-- kanji recognition/recall in a single deck.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER NOT NULL
);

-- ----------------------------------------------------------------------------
-- Reference content (populated by scripts/import_*.py, shipped in kanji.db)
-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS kanji (
    id           INTEGER PRIMARY KEY,
    literal      TEXT    NOT NULL UNIQUE,
    stroke_count INTEGER NOT NULL,
    grade        INTEGER,          -- Jouyou grade (1-6, 8, 9, 10) from KANJIDIC2
    jlpt         INTEGER,          -- modern JLPT level (5=N5 .. 1=N1), from resources/jlpt/*.txt
    jlpt_old     INTEGER,          -- legacy pre-2010 JLPT level in KANJIDIC2 (4=easiest); reference only
    frequency    INTEGER,          -- newspaper frequency rank (1 = most common), if in the top ~2500
    radical      TEXT
);
CREATE INDEX IF NOT EXISTS idx_kanji_jlpt ON kanji(jlpt);
CREATE INDEX IF NOT EXISTS idx_kanji_grade ON kanji(grade);

-- KanjiVG stroke-order data: one SVG document per kanji (CC BY-SA 3.0, KanjiVG).
CREATE TABLE IF NOT EXISTS kanjivg (
    kanji_id     INTEGER PRIMARY KEY REFERENCES kanji(id) ON DELETE CASCADE,
    stroke_count INTEGER NOT NULL,
    svg          TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS reading (
    id       INTEGER PRIMARY KEY,
    kanji_id INTEGER NOT NULL REFERENCES kanji(id) ON DELETE CASCADE,
    type     TEXT    NOT NULL CHECK (type IN ('on', 'kun', 'nanori')),
    value    TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_reading_kanji ON reading(kanji_id);

CREATE TABLE IF NOT EXISTS meaning (
    id       INTEGER PRIMARY KEY,
    kanji_id INTEGER NOT NULL REFERENCES kanji(id) ON DELETE CASCADE,
    value    TEXT    NOT NULL,
    lang     TEXT    NOT NULL DEFAULT 'en'
);
CREATE INDEX IF NOT EXISTS idx_meaning_kanji ON meaning(kanji_id);

CREATE TABLE IF NOT EXISTS vocab (
    id         INTEGER PRIMARY KEY,
    expression TEXT    NOT NULL,
    kana       TEXT    NOT NULL,
    jlpt       INTEGER,   -- level of the word's hardest component kanji
    grade      INTEGER,   -- latest school grade among the word's component kanji
    frequency  INTEGER    -- coarse rank from JMdict 'nfXX' bands (1 = most common)
);
CREATE INDEX IF NOT EXISTS idx_vocab_jlpt ON vocab(jlpt);
CREATE INDEX IF NOT EXISTS idx_vocab_grade ON vocab(grade);

CREATE TABLE IF NOT EXISTS vocab_gloss (
    id       INTEGER PRIMARY KEY,
    vocab_id INTEGER NOT NULL REFERENCES vocab(id) ON DELETE CASCADE,
    value    TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_vocab_gloss_vocab ON vocab_gloss(vocab_id);

CREATE TABLE IF NOT EXISTS vocab_kanji (
    vocab_id INTEGER NOT NULL REFERENCES vocab(id) ON DELETE CASCADE,
    kanji_id INTEGER NOT NULL REFERENCES kanji(id) ON DELETE CASCADE,
    PRIMARY KEY (vocab_id, kanji_id)
);

-- Example sentences (Tanaka Corpus / Tatoeba, CC BY-SA, EDRDG).
CREATE TABLE IF NOT EXISTS sentence (
    id         INTEGER PRIMARY KEY,
    japanese   TEXT    NOT NULL,
    english    TEXT    NOT NULL,
    length     INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS vocab_sentence (
    vocab_id    INTEGER NOT NULL REFERENCES vocab(id) ON DELETE CASCADE,
    sentence_id INTEGER NOT NULL REFERENCES sentence(id) ON DELETE CASCADE,
    PRIMARY KEY (vocab_id, sentence_id)
);
CREATE INDEX IF NOT EXISTS idx_vocab_sentence_vocab ON vocab_sentence(vocab_id);

-- ----------------------------------------------------------------------------
-- Study state (lives in the per-user study.db)
-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS deck (
    id              INTEGER PRIMARY KEY,
    name            TEXT    NOT NULL,
    kind            TEXT    NOT NULL DEFAULT 'kanji'
                            CHECK (kind IN ('kanji', 'vocab', 'mixed')),
    description     TEXT    NOT NULL DEFAULT '',
    new_per_day     INTEGER NOT NULL DEFAULT 10,
    reviews_per_day INTEGER NOT NULL DEFAULT 200,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS card (
    id            INTEGER PRIMARY KEY,
    deck_id       INTEGER NOT NULL REFERENCES deck(id) ON DELETE CASCADE,
    subject_type  TEXT    NOT NULL CHECK (subject_type IN ('kanji', 'vocab')),
    subject_id    INTEGER NOT NULL,
    mode          TEXT    NOT NULL
                          CHECK (mode IN ('recognition', 'recall', 'stroke')),
    state         TEXT    NOT NULL DEFAULT 'new'
                          CHECK (state IN ('new', 'learning', 'review', 'relearning')),
    step              INTEGER NOT NULL DEFAULT 0,
    due               TEXT    NOT NULL,
    stability         REAL,
    difficulty        REAL,
    reps              INTEGER NOT NULL DEFAULT 0,
    lapses            INTEGER NOT NULL DEFAULT 0,
    last_reviewed_at  TEXT,
    created_at        TEXT    NOT NULL DEFAULT (datetime('now')),
    UNIQUE (deck_id, subject_type, subject_id, mode)
);
CREATE INDEX IF NOT EXISTS idx_card_due ON card(deck_id, due);

CREATE TABLE IF NOT EXISTS review_log (
    id             INTEGER PRIMARY KEY,
    card_id        INTEGER NOT NULL REFERENCES card(id) ON DELETE CASCADE,
    reviewed_at    TEXT    NOT NULL,
    rating         INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 4),
    elapsed_ms     INTEGER NOT NULL DEFAULT 0,
    prev_due       TEXT    NOT NULL,
    new_due        TEXT    NOT NULL,
    prev_stability REAL    NOT NULL DEFAULT 0,
    new_stability  REAL    NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_review_log_card ON review_log(card_id);
CREATE INDEX IF NOT EXISTS idx_review_log_time ON review_log(reviewed_at);

CREATE TABLE IF NOT EXISTS setting (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
