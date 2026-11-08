//! Experimental length-major phrase codec (`lenmin v1`).
//!
//! Not a replacement for [`crate::encode_u64`], phrase v2-v4 or
//! [`crate::phrase_dyn`]. A model is an acyclic word automaton (states with an
//! accept flag and prefix-free rows of tokens) plus a range of word counts. A
//! phrase is `k` words joined by single spaces. All valid phrases are ordered
//! by total length (letters plus spaces), then by word count, then by the
//! length and rank of the first word, the second word, and so on. The `u64`
//! value is the position in that order, so the 2^64 *shortest* phrases are
//! used and values at or above 2^64 never decode. Counts are exact `u128`
//! (checked); small values map to short phrases, so callers that want
//! structured inputs spread out may apply [`mix`] first (a separate,
//! invertible, non-cryptographic step).

pub use crate::phrase_dyn::{mix, unmix};

/// Error building a model.
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum ModelError {
    /// Malformed text, bad state reference, cycle, empty or conflicting tokens.
    Invalid(&'static str),
    /// Exact counts do not fit into `u128`.
    CountOverflow,
    /// Fewer than 2^64 valid phrases.
    InsufficientCapacity,
}

#[derive(Clone, Debug)]
struct Choice {
    text: String,
    width: usize,
    next: usize,
}

#[derive(Clone, Debug)]
struct State {
    accept: bool,
    choices: Vec<Choice>,
}

/// One length class: `(word_count, letters, number_of_phrases)`.
type ClassEntry = (usize, usize, u128);

/// A validated model with its exact count tables.
#[derive(Clone, Debug)]
pub struct Model {
    name: String,
    words_min: usize,
    words_max: usize,
    states: Vec<State>,
    max_letters: usize,
    /// `counts[state][remaining]`: words with exactly `remaining` letters.
    counts: Vec<Vec<u128>>,
    /// `sequences[k][letters]`: ordered `k`-word sequences.
    sequences: Vec<Vec<u128>>,
    /// Total phrase lengths present, ascending.
    lengths: Vec<usize>,
    classes: Vec<Vec<ClassEntry>>,
    /// `cumulative[i]` = phrases shorter than `lengths[i]`.
    cumulative: Vec<u128>,
    limit: u128,
}

const MAX_STATES: usize = 200_000;

impl Model {
    /// Parse a `lenmin v1` model (see `models/overnight/compile_lenmin.py`).
    pub fn parse(source: &str) -> Result<Self, ModelError> {
        Self::parse_with_limit(source, 1u128 << 64)
    }

    /// Parse with a custom number of required/valid values (reduced models in tests).
    #[doc(hidden)]
    pub fn parse_with_limit(source: &str, limit: u128) -> Result<Self, ModelError> {
        let invalid = ModelError::Invalid;
        let mut lines = source.split('\n');
        if lines.next() != Some("lenmin v1") {
            return Err(invalid("header"));
        }
        let name = lines
            .next()
            .and_then(|line| line.strip_prefix("name "))
            .ok_or(invalid("name"))?
            .to_owned();
        let words_field = lines
            .next()
            .and_then(|line| line.strip_prefix("words "))
            .ok_or(invalid("words"))?;
        let bounds: Vec<usize> = words_field
            .split(' ')
            .map(|part| part.parse::<usize>().map_err(|_| invalid("words")))
            .collect::<Result<_, _>>()?;
        let (words_min, words_max) = match bounds.as_slice() {
            [only] => (*only, *only),
            [low, high] => (*low, *high),
            _ => return Err(invalid("words")),
        };
        if words_min == 0 || words_min > words_max || words_max > 8 {
            return Err(invalid("words range"));
        }
        let count: usize = lines
            .next()
            .and_then(|line| line.strip_prefix("states "))
            .and_then(|rest| rest.parse().ok())
            .ok_or(invalid("states"))?;
        if count == 0 || count > MAX_STATES {
            return Err(invalid("state count"));
        }
        let mut states = Vec::with_capacity(count);
        for index in 0..count {
            let line = lines.next().ok_or(invalid("missing state"))?;
            let (flag, rest) = line.split_once('|').ok_or(invalid("state flag"))?;
            let accept = match flag {
                "A" => true,
                "N" => false,
                _ => return Err(invalid("state flag")),
            };
            let mut choices: Vec<Choice> = Vec::new();
            if !rest.is_empty() {
                for item in rest.split(' ') {
                    let (text, target) = item.rsplit_once('>').ok_or(invalid("choice"))?;
                    let next: usize = target.parse().map_err(|_| invalid("target"))?;
                    if text.is_empty()
                        || next <= index
                        || next >= count
                        || !text
                            .chars()
                            .all(|letter| letter.is_alphabetic() && !letter.is_uppercase())
                    {
                        return Err(invalid("choice content"));
                    }
                    if choices.iter().any(|other| {
                        other.text.starts_with(text) || text.starts_with(other.text.as_str())
                    }) {
                        return Err(invalid("row not prefix-free"));
                    }
                    choices.push(Choice {
                        text: text.to_owned(),
                        width: text.chars().count(),
                        next,
                    });
                }
            }
            if !accept && choices.is_empty() {
                return Err(invalid("dead state"));
            }
            states.push(State { accept, choices });
        }
        if lines.any(|line| !line.is_empty()) || states[0].accept {
            return Err(invalid("trailing data or accepting start"));
        }
        Self::build(name, words_min, words_max, states, limit)
    }

    fn build(
        name: String,
        words_min: usize,
        words_max: usize,
        states: Vec<State>,
        limit: u128,
    ) -> Result<Self, ModelError> {
        let mut longest = vec![0usize; states.len()];
        for index in (0..states.len()).rev() {
            longest[index] = states[index]
                .choices
                .iter()
                .map(|choice| choice.width + longest[choice.next])
                .max()
                .unwrap_or(0);
        }
        let max_letters = longest[0];
        let mut counts = vec![vec![0u128; max_letters + 1]; states.len()];
        for index in (0..states.len()).rev() {
            let mut table = vec![0u128; max_letters + 1];
            if states[index].accept {
                table[0] = 1;
            }
            for choice in &states[index].choices {
                for remaining in choice.width..=max_letters {
                    table[remaining] = table[remaining]
                        .checked_add(counts[choice.next][remaining - choice.width])
                        .ok_or(ModelError::CountOverflow)?;
                }
            }
            counts[index] = table;
        }
        let mut sequences: Vec<Vec<u128>> = vec![vec![1]];
        for words in 1..=words_max {
            let previous = &sequences[words - 1];
            let mut current = vec![0u128; words * max_letters + 1];
            for (total, slot) in current.iter_mut().enumerate() {
                for (letters, &word_total) in counts[0]
                    .iter()
                    .enumerate()
                    .skip(1)
                    .take(max_letters.min(total))
                {
                    if let Some(tail) = previous.get(total - letters) {
                        let product = word_total
                            .checked_mul(*tail)
                            .ok_or(ModelError::CountOverflow)?;
                        *slot = slot.checked_add(product).ok_or(ModelError::CountOverflow)?;
                    }
                }
            }
            sequences.push(current);
        }
        let mut by_length: std::collections::BTreeMap<usize, Vec<ClassEntry>> =
            std::collections::BTreeMap::new();
        for (words, row) in sequences
            .iter()
            .enumerate()
            .take(words_max + 1)
            .skip(words_min)
        {
            for (letters, &value) in row.iter().enumerate() {
                if value != 0 {
                    by_length
                        .entry(letters + words - 1)
                        .or_default()
                        .push((words, letters, value));
                }
            }
        }
        let mut lengths = Vec::new();
        let mut classes = Vec::new();
        let mut cumulative = Vec::new();
        let mut running = 0u128;
        for (length, entries) in by_length {
            cumulative.push(running);
            for entry in &entries {
                running = running
                    .checked_add(entry.2)
                    .ok_or(ModelError::CountOverflow)?;
            }
            lengths.push(length);
            classes.push(entries);
        }
        if running < limit {
            return Err(ModelError::InsufficientCapacity);
        }
        Ok(Self {
            name,
            words_min,
            words_max,
            states,
            max_letters,
            counts,
            sequences,
            lengths,
            classes,
            cumulative,
            limit,
        })
    }

    /// Model name from the header.
    pub fn name(&self) -> &str {
        &self.name
    }

    /// Inclusive word-count range.
    pub fn word_range(&self) -> (usize, usize) {
        (self.words_min, self.words_max)
    }

    /// Number of distinct valid phrases (>= 2^64 for real models).
    pub fn capacity(&self) -> u128 {
        self.cumulative.last().map_or(0, |last| {
            last + self
                .classes
                .last()
                .map_or(0, |entries| entries.iter().map(|entry| entry.2).sum())
        })
    }

    /// Exact `(total length, number of u64 values)` pairs, ascending length.
    pub fn length_histogram(&self) -> Vec<(usize, u128)> {
        let mut remaining = self.limit;
        let mut histogram = Vec::new();
        for (length, entries) in self.lengths.iter().zip(&self.classes) {
            if remaining == 0 {
                break;
            }
            let take = entries
                .iter()
                .map(|entry| entry.2)
                .sum::<u128>()
                .min(remaining);
            histogram.push((*length, take));
            remaining -= take;
        }
        histogram
    }

    fn unrank_word(&self, letters: usize, mut rank: u128) -> String {
        let mut text = String::new();
        let mut state = 0usize;
        let mut remaining = letters;
        while remaining > 0 {
            let mut chosen = None;
            for choice in &self.states[state].choices {
                if choice.width > remaining {
                    continue;
                }
                let size = self.counts[choice.next][remaining - choice.width];
                if rank < size {
                    chosen = Some(choice);
                    break;
                }
                rank -= size;
            }
            let choice = chosen.expect("rank below word count");
            text.push_str(&choice.text);
            remaining -= choice.width;
            state = choice.next;
        }
        text
    }

    fn parse_word(&self, word: &str) -> Option<(usize, u128)> {
        let letters = word.chars().count();
        if letters == 0 || letters > self.max_letters {
            return None;
        }
        let (mut state, mut remaining, mut rank, mut rest) = (0usize, letters, 0u128, word);
        while !rest.is_empty() {
            let mut matched = None;
            for choice in &self.states[state].choices {
                if rest.starts_with(choice.text.as_str()) {
                    matched = Some(choice);
                    break;
                }
                if choice.width <= remaining {
                    rank += self.counts[choice.next][remaining - choice.width];
                }
            }
            let choice = matched?;
            rest = &rest[choice.text.len()..];
            remaining -= choice.width;
            state = choice.next;
        }
        self.states[state].accept.then_some((letters, rank))
    }

    /// Encode any `u64` (every `u64` is valid for a real model).
    pub fn encode(&self, value: u64) -> String {
        let value = u128::from(value);
        let index = self.cumulative.partition_point(|&start| start <= value) - 1;
        let mut rest = value - self.cumulative[index];
        let mut shape = None;
        for &(words, letters, count) in &self.classes[index] {
            if rest < count {
                shape = Some((words, letters));
                break;
            }
            rest -= count;
        }
        let (words, mut left) = shape.expect("value below capacity");
        let mut parts = Vec::with_capacity(words);
        for position in 0..words {
            let tail = &self.sequences[words - position - 1];
            let mut length = 0;
            for candidate in 1..=self.max_letters.min(left) {
                let Some(&tail_count) = tail.get(left - candidate) else {
                    continue;
                };
                let block = self.counts[0][candidate] * tail_count;
                if rest < block {
                    length = candidate;
                    break;
                }
                rest -= block;
            }
            let tail_count = tail[left - length];
            parts.push(self.unrank_word(length, rest / tail_count));
            rest %= tail_count;
            left -= length;
        }
        parts.join(" ")
    }

    /// Decode a canonical phrase (single spaces, exact lowercase tokens).
    pub fn decode(&self, phrase: &str) -> Option<u64> {
        let parts: Vec<&str> = phrase.split(' ').collect();
        let words = parts.len();
        if words < self.words_min || words > self.words_max {
            return None;
        }
        let parsed: Vec<(usize, u128)> = parts
            .iter()
            .map(|part| self.parse_word(part))
            .collect::<Option<_>>()?;
        let letters: usize = parsed.iter().map(|item| item.0).sum();
        let length = letters + words - 1;
        let index = self.lengths.binary_search(&length).ok()?;
        let mut value = self.cumulative[index];
        for &(count_words, _, count) in &self.classes[index] {
            if count_words == words {
                break;
            }
            value += count;
        }
        let mut left = letters;
        for (position, &(word_letters, rank)) in parsed.iter().enumerate() {
            let tail = &self.sequences[words - position - 1];
            for shorter in 1..word_letters {
                if let Some(&tail_count) = tail.get(left - shorter) {
                    value += self.counts[0][shorter] * tail_count;
                }
            }
            value += rank * tail[left - word_letters];
            left -= word_letters;
        }
        if value < self.limit {
            u64::try_from(value).ok()
        } else {
            None
        }
    }
}

/// Frozen experimental models, generated by `models/overnight/compile_lenmin.py`.
pub mod models {
    /// English unique-word model, selected by the sweep (see OVERNIGHT_REPORT.md).
    pub const EN_UNIQUE: &str = include_str!("lenmin_models/en-unique.txt");
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::HashSet;

    /// Same toy automaton as `models/overnight/test_lenmin.py`.
    const TOY: &str =
        "lenmin v1\nname toy\nwords 1 3\nstates 4\nN|a>1 bc>3 d>2 ef>1\nA|x>2 yy>2\nA|z>3\nA|\n";

    fn brute_force_phrases(model_text: &str, kmin: usize, kmax: usize) -> Vec<String> {
        let model = Model::parse_with_limit(model_text, 1).unwrap();
        fn walk(model: &Model, state: usize, text: String, out: &mut Vec<String>) {
            if model.states[state].accept && !text.is_empty() {
                out.push(text.clone());
            }
            for choice in &model.states[state].choices {
                walk(model, choice.next, format!("{text}{}", choice.text), out);
            }
        }
        let mut words = Vec::new();
        walk(&model, 0, String::new(), &mut words);
        let mut phrases = Vec::new();
        let mut level: Vec<String> = vec![String::new()];
        for count in 1..=kmax {
            let mut next = Vec::new();
            for prefix in &level {
                for word in &words {
                    next.push(if prefix.is_empty() {
                        word.clone()
                    } else {
                        format!("{prefix} {word}")
                    });
                }
            }
            if count >= kmin {
                phrases.extend(next.iter().cloned());
            }
            level = next;
        }
        phrases
    }

    #[test]
    fn toy_model_exhaustive_bijection_and_length_major() {
        let phrases = brute_force_phrases(TOY, 1, 3);
        let model = Model::parse_with_limit(TOY, 1).unwrap();
        let capacity = model.capacity();
        assert_eq!(capacity, phrases.len() as u128);
        let full = Model::parse_with_limit(TOY, capacity).unwrap();
        let produced: Vec<String> = (0..capacity as u64).map(|v| full.encode(v)).collect();
        let produced_set: HashSet<&String> = produced.iter().collect();
        assert_eq!(produced_set.len(), produced.len());
        assert_eq!(
            produced_set,
            phrases.iter().collect::<HashSet<_>>(),
            "image equals the brute-force set"
        );
        assert!(
            produced
                .windows(2)
                .all(|pair| pair[0].len() <= pair[1].len())
        );
        for (value, phrase) in produced.iter().enumerate() {
            assert_eq!(full.decode(phrase), Some(value as u64));
        }
        // Everything over a small alphabet decodes iff it is a produced phrase.
        let alphabet: Vec<char> = "abcdefxyz ".chars().collect();
        let mut text = vec![0usize];
        let mut checked = 0;
        for size in 1..=5usize {
            text.clear();
            text.resize(size, 0);
            loop {
                let candidate: String = text.iter().map(|&i| alphabet[i]).collect();
                assert_eq!(
                    full.decode(&candidate).is_some(),
                    produced_set.contains(&candidate),
                    "{candidate:?}"
                );
                checked += 1;
                let mut place = size;
                while place > 0 {
                    place -= 1;
                    text[place] += 1;
                    if text[place] < alphabet.len() {
                        break;
                    }
                    text[place] = 0;
                }
                if text.iter().all(|&i| i == 0) {
                    break;
                }
            }
        }
        assert!(checked > 100_000);
    }

    #[test]
    fn toy_truncated_limit_matches_prefix() {
        let full_count = brute_force_phrases(TOY, 1, 3).len() as u128;
        let full = Model::parse_with_limit(TOY, full_count).unwrap();
        let cut = Model::parse_with_limit(TOY, 10).unwrap();
        for value in 0..10u64 {
            assert_eq!(cut.encode(value), full.encode(value));
        }
        assert_eq!(full.decode(&full.encode(10)), Some(10));
        assert_eq!(cut.decode(&full.encode(10)), None);
    }

    #[test]
    fn invalid_models_rejected() {
        for text in [
            "",
            "lenmin v2\nname r\nwords 1\nstates 1\nA|\n",
            "lenmin v1\nname r\nwords 0\nstates 1\nN|a>0\n",
            "lenmin v1\nname r\nwords 1\nstates 2\nN|a>1 ab>1\nA|\n",
            "lenmin v1\nname r\nwords 1\nstates 2\nN|a>0\nA|\n",
            "lenmin v1\nname r\nwords 1\nstates 2\nN|A>1\nA|\n",
            "lenmin v1\nname r\nwords 1\nstates 2\nN|a>1\nN|\n",
            "lenmin v1\nname r\nwords 1\nstates 2\nA|a>1\nA|\n",
            "lenmin v1\nname r\nwords 1\nstates 2\nN|a>1\nA|\nextra\n",
            "lenmin v1\nname r\nwords 1\nstates 2\nN|a>9\nA|\n",
            "lenmin v1\nname r\nwords 1\nstates 2\nN|a b>1\nA|\n",
        ] {
            assert!(
                matches!(
                    Model::parse_with_limit(text, 1),
                    Err(ModelError::Invalid(_))
                ),
                "{text:?}"
            );
        }
        assert_eq!(
            Model::parse("lenmin v1\nname r\nwords 3\nstates 2\nN|a>1 b>1\nA|\n").unwrap_err(),
            ModelError::InsufficientCapacity
        );
    }

    fn edge_values() -> Vec<u64> {
        vec![
            0,
            1,
            2,
            42,
            1000,
            123_456_789,
            (1 << 63) - 1,
            1 << 63,
            u64::MAX - 1,
            u64::MAX,
        ]
    }

    fn check_model(source: &str) -> Model {
        let model = Model::parse(source).unwrap();
        assert!(model.capacity() >= 1u128 << 64);
        let (low, _) = model.word_range();
        for value in edge_values() {
            let phrase = model.encode(value);
            assert_eq!(model.decode(&phrase), Some(value), "{phrase}");
            let mut invalid = vec![
                format!(" {phrase}"),
                format!("{phrase} "),
                phrase.replace(' ', "  "),
                phrase.replace(' ', "\t"),
                phrase.replace(' ', "-"),
                phrase.to_uppercase(),
                format!("{phrase}x"),
                phrase.replace(' ', ""),
                String::new(),
                " ".into(),
            ];
            if low > 1 {
                invalid.push(phrase.split(' ').next().unwrap().to_owned());
            }
            for text in invalid {
                if let Some(other) = model.decode(&text) {
                    // A different string may legitimately be another phrase,
                    // but it must then be the canonical spelling of `other`.
                    assert_eq!(model.encode(other), text, "{text:?}");
                    assert_ne!(other, value, "{text:?}");
                }
            }
            assert_eq!(model.decode(&phrase.to_uppercase()), None);
            assert_eq!(model.decode(&phrase.replace(' ', "  ")), None);
            assert_eq!(model.decode(&format!(" {phrase}")), None);
            assert_eq!(model.decode(&format!("{phrase} ")), None);
        }
        let histogram = model.length_histogram();
        assert_eq!(
            histogram.iter().map(|item| item.1).sum::<u128>(),
            1u128 << 64
        );
        model
    }

    #[test]
    fn en_unique_edges_roundtrip_uniqueness_and_order() {
        let model = check_model(models::EN_UNIQUE);
        let mut seen = HashSet::new();
        let mut state = 0x9e37_79b9_7f4a_7c15u64;
        let mut values = Vec::new();
        for _ in 0..100_000 {
            state = state
                .wrapping_mul(6364136223846793005)
                .wrapping_add(1442695040888963407);
            let phrase = model.encode(state);
            assert_eq!(model.decode(&phrase), Some(state));
            assert!(seen.insert(phrase));
            values.push(state);
        }
        values.sort_unstable();
        let lengths: Vec<usize> = values
            .iter()
            .map(|&value| model.encode(value).chars().count())
            .collect();
        assert!(
            lengths.windows(2).all(|pair| pair[0] <= pair[1]),
            "length-major"
        );
        // mix is a bijection and composes with the codec.
        for value in edge_values() {
            assert_eq!(unmix(mix(value)), value);
            assert_eq!(
                model.decode(&model.encode(mix(value))).map(unmix),
                Some(value)
            );
        }
    }

    #[test]
    fn pinned_vectors_match_python_reference() {
        let model = Model::parse(models::EN_UNIQUE).unwrap();
        for (value, phrase) in [
            (0u64, "to to"),
            (42, "of up"),
            (123_456_789, "so zincamah"),
            (u64::MAX, "geoglovid fruir braxxcue"),
        ] {
            assert_eq!(model.encode(value), phrase);
            assert_eq!(model.decode(phrase), Some(value));
        }
    }

    #[test]
    fn values_beyond_range_do_not_decode() {
        let model = Model::parse(models::EN_UNIQUE).unwrap();
        let (length, longest) = *model.length_histogram().last().unwrap();
        let last = model.encode(u64::MAX);
        assert_eq!(last.chars().count(), length);
        assert_eq!(model.decode(&last), Some(u64::MAX));
        let index = model.lengths.binary_search(&length).unwrap();
        let class_total: u128 = model.classes[index].iter().map(|entry| entry.2).sum();
        assert!(class_total > longest, "last used class must be truncated");
    }
}
