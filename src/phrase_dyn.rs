//! Experimental bounded-grammar rank/unrank phrase codec ("dyn v1").
//!
//! This is *not* a replacement for [`crate::encode_u64`] or the phrase v2-v4
//! formats, and its models are not frozen interchange formats beyond the
//! version string embedded in each model.
//!
//! A word is produced by an acyclic automaton: every choice emits a nonempty
//! token and either moves to a strictly later state or ends the word. Choices
//! of one state are prefix-free over their emitted UTF-8 text, so a word is
//! parsed deterministically. `W` is the number of complete words. A phrase is
//! `words` words separated by single spaces; a `u64` is written in base `W`,
//! first word most significant, and each digit is unranked through
//! contiguous intervals sized by subtree completion counts. Ranks at or above
//! 2^64 are rejected on decode. All arithmetic is checked `u128`.

/// Error building a model.
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum ModelError {
    /// Malformed text, bad state reference, cycle, empty or conflicting tokens.
    Invalid(&'static str),
    /// Completion counts do not fit into `u128`.
    CountOverflow,
    /// `W^words < 2^64`.
    InsufficientCapacity,
}

#[derive(Clone, Debug)]
struct Choice {
    text: String,
    /// `None` ends the word.
    next: Option<usize>,
}

/// A validated grammar with its completion-count table.
#[derive(Clone, Debug)]
pub struct Model {
    name: String,
    words: usize,
    states: Vec<Vec<Choice>>,
    counts: Vec<u128>,
    width: u128,
}

impl Model {
    /// Parse a `dynphrase v1` model (see `models/overnight/compile_dyn.py`).
    pub fn parse(source: &str) -> Result<Self, ModelError> {
        let mut lines = source.lines();
        if lines.next() != Some("dynphrase v1") {
            return Err(ModelError::Invalid("header"));
        }
        let mut field = |key: &str| -> Result<String, ModelError> {
            lines
                .next()
                .and_then(|line| line.strip_prefix(key))
                .and_then(|rest| rest.strip_prefix(' '))
                .map(str::to_owned)
                .ok_or(ModelError::Invalid("field"))
        };
        let name = field("name")?;
        let words: usize = field("words")?
            .parse()
            .map_err(|_| ModelError::Invalid("words"))?;
        let state_count: usize = field("states")?
            .parse()
            .map_err(|_| ModelError::Invalid("states"))?;
        let mut states = Vec::with_capacity(state_count);
        for (index, line) in lines.enumerate() {
            let mut choices: Vec<Choice> = Vec::new();
            for item in line.split(' ') {
                let (text, target) = item.rsplit_once('>').ok_or(ModelError::Invalid("choice"))?;
                let next = if target == "$" {
                    None
                } else {
                    let next: usize = target.parse().map_err(|_| ModelError::Invalid("target"))?;
                    if next <= index || next >= state_count {
                        return Err(ModelError::Invalid("target order"));
                    }
                    Some(next)
                };
                if text.is_empty()
                    || text
                        .chars()
                        .any(|character| !character.is_alphabetic() || character.is_uppercase())
                    || choices
                        .iter()
                        .any(|other| other.text.starts_with(text) || text.starts_with(&other.text))
                {
                    return Err(ModelError::Invalid("token"));
                }
                choices.push(Choice {
                    text: text.to_owned(),
                    next,
                });
            }
            states.push(choices);
        }
        if states.len() != state_count || state_count == 0 || words == 0 {
            return Err(ModelError::Invalid("state count"));
        }
        let mut counts = vec![0u128; state_count];
        for index in (0..state_count).rev() {
            let mut total = 0u128;
            for choice in &states[index] {
                let size = choice.next.map_or(1, |next| counts[next]);
                total = total.checked_add(size).ok_or(ModelError::CountOverflow)?;
            }
            counts[index] = total;
        }
        let width = counts[0];
        let mut capacity = 1u128;
        for _ in 0..words {
            match capacity.checked_mul(width) {
                Some(value) => capacity = value,
                None => {
                    capacity = u128::MAX;
                    break;
                }
            }
        }
        if capacity < 1u128 << 64 {
            return Err(ModelError::InsufficientCapacity);
        }
        Ok(Self {
            name,
            words,
            states,
            counts,
            width,
        })
    }

    /// Model identifier, e.g. `en-unique-cap256-w3`.
    pub fn name(&self) -> &str {
        &self.name
    }

    /// Number of distinct complete words (`W`).
    pub fn word_count(&self) -> u128 {
        self.width
    }

    /// Words per phrase.
    pub fn words(&self) -> usize {
        self.words
    }

    fn size(&self, choice: &Choice) -> u128 {
        choice.next.map_or(1, |next| self.counts[next])
    }

    /// Word for `rank < W`.
    pub fn unrank_word(&self, mut rank: u128) -> Option<String> {
        if rank >= self.width {
            return None;
        }
        let mut state = 0;
        let mut output = String::new();
        loop {
            let mut selected = None;
            for choice in &self.states[state] {
                let size = self.size(choice);
                if rank < size {
                    selected = Some(choice);
                    break;
                }
                rank -= size;
            }
            let choice = selected?;
            output.push_str(&choice.text);
            match choice.next {
                Some(next) => state = next,
                None => return Some(output),
            }
        }
    }

    /// Rank of a canonical word, or `None` if it is not a codeword.
    pub fn rank_word(&self, mut word: &str) -> Option<u128> {
        let mut state = 0;
        let mut rank = 0u128;
        loop {
            let mut selected = None;
            for choice in &self.states[state] {
                if word.starts_with(choice.text.as_str()) {
                    selected = Some(choice);
                    break;
                }
                rank += self.size(choice);
            }
            let choice = selected?;
            word = &word[choice.text.len()..];
            match choice.next {
                Some(next) => state = next,
                None => return word.is_empty().then_some(rank),
            }
        }
    }

    /// Encode every bit of `value`; never fails for a validated model.
    pub fn encode(&self, value: u64) -> String {
        let mut rest = u128::from(value);
        let mut digits = vec![0u128; self.words];
        for digit in digits.iter_mut().rev() {
            *digit = rest % self.width;
            rest /= self.width;
        }
        digits
            .into_iter()
            .map(|digit| self.unrank_word(digit).expect("digit below W"))
            .collect::<Vec<_>>()
            .join(" ")
    }

    /// Decode a canonical phrase (exact single spaces, NFC lowercase text).
    pub fn decode(&self, phrase: &str) -> Option<u64> {
        let parts: Vec<&str> = phrase.split(' ').collect();
        if parts.len() != self.words {
            return None;
        }
        let mut value = 0u128;
        for part in parts {
            let rank = self.rank_word(part)?;
            value = value.checked_mul(self.width)?.checked_add(rank)?;
        }
        u64::try_from(value).ok()
    }
}

/// Optional, separately versioned ("mix v1") reversible bijection on u64
/// (splitmix64 finalizer) to spread structured inputs such as 0, 1, 2 before
/// encoding. It is *not* encryption and does not remove repetition; examples
/// must also show unmixed values.
pub fn mix(mut value: u64) -> u64 {
    value ^= value >> 30;
    value = value.wrapping_mul(0xbf58_476d_1ce4_e5b9);
    value ^= value >> 27;
    value = value.wrapping_mul(0x94d0_49bb_1331_11eb);
    value ^ (value >> 31)
}

/// Inverse of [`mix`].
pub fn unmix(mut value: u64) -> u64 {
    value = unshift(value, 31).wrapping_mul(0x3196_42b2_d24d_8ec3);
    value = unshift(value, 27).wrapping_mul(0x96de_1b17_3f11_9089);
    unshift(value, 30)
}

fn unshift(value: u64, shift: u32) -> u64 {
    let mut result = value;
    let mut step = shift;
    while step < 64 {
        result = value ^ (result >> shift);
        step += shift;
    }
    result
}

/// Frozen experimental models, generated by `models/overnight/compile_dyn.py`.
pub mod models {
    /// English, v3 vocabulary, 94,080-word unique list (cap 32, <=5 tokens).
    pub const EN_UNIQUE: &str = include_str!("dyn_models/en-unique.txt");
    /// English, v3 vocabulary, FineWeb sample occurrence weights (cap 64).
    pub const EN_FINEWEB: &str = include_str!("dyn_models/en-fineweb.txt");
    /// Turkish native Unicode, FineWeb2 tur_Latn sample (cap 32).
    pub const TR_FINEWEB: &str = include_str!("dyn_models/tr-fineweb.txt");
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::HashSet;

    /// Reduced model: W = 2 + 3*(1+2) = 11 words... built so W^2 >= 2^64 is
    /// impossible; use the internal word API with a tiny phrase width instead.
    fn reduced() -> Model {
        // Bypass the capacity check by building directly, then exercise the
        // same unrank/rank code paths used by real models.
        let states = vec![
            vec![
                Choice {
                    text: "ka".into(),
                    next: Some(1),
                },
                Choice {
                    text: "lo".into(),
                    next: Some(2),
                },
                Choice {
                    text: "m".into(),
                    next: None,
                },
            ],
            vec![
                Choice {
                    text: "ri".into(),
                    next: Some(2),
                },
                Choice {
                    text: "n".into(),
                    next: None,
                },
                Choice {
                    text: "sa".into(),
                    next: None,
                },
            ],
            vec![
                Choice {
                    text: "t".into(),
                    next: None,
                },
                Choice {
                    text: "va".into(),
                    next: None,
                },
            ],
        ];
        Model {
            name: "reduced".into(),
            words: 1,
            counts: vec![7, 4, 2],
            width: 7,
            states,
        }
    }

    #[test]
    fn reduced_model_exhaustive_bijection() {
        let model = reduced();
        // Independently enumerate every path in choice order.
        let mut expected = Vec::new();
        fn walk(model: &Model, state: usize, prefix: String, out: &mut Vec<String>) {
            for choice in &model.states[state] {
                let text = prefix.clone() + &choice.text;
                match choice.next {
                    Some(next) => walk(model, next, text, out),
                    None => out.push(text),
                }
            }
        }
        walk(&model, 0, String::new(), &mut expected);
        // counts recomputed: state2=2, state1=2+1+1=4, state0=4+2+1=7
        assert_eq!(expected.len(), 7);
        for (rank, word) in expected.iter().enumerate() {
            assert_eq!(
                model.unrank_word(rank as u128).as_deref(),
                Some(word.as_str())
            );
            assert_eq!(model.rank_word(word), Some(rank as u128));
            for end in 0..word.len() {
                assert_eq!(model.rank_word(&word[..end]), None, "prefix {word}");
            }
            assert_eq!(model.rank_word(&format!("{word}t")), None);
        }
        assert_eq!(model.unrank_word(7), None);
        assert_eq!(expected.iter().collect::<HashSet<_>>().len(), 7);
    }

    #[test]
    fn reduced_model_counts_match_parser() {
        let text =
            "dynphrase v1\nname r\nwords 23\nstates 3\nka>1 lo>2 m>$\nri>2 n>$ sa>$\nt>$ va>$\n";
        let model = Model::parse(text).unwrap();
        assert_eq!(model.word_count(), 7);
        let reduced = reduced();
        for rank in 0..7 {
            assert_eq!(model.unrank_word(rank), reduced.unrank_word(rank));
        }
        // 7^23 >= 2^64: exercise full phrase codec on the reduced grammar.
        for value in [0, 1, 2, 42, u64::MAX - 1, u64::MAX] {
            assert_eq!(model.decode(&model.encode(value)), Some(value));
        }
        // 7^23 > 2^64, so the largest phrase is out of range.
        assert_eq!(model.decode(&vec!["va"; 23].join(" ")), None);
    }

    #[test]
    fn invalid_models_rejected() {
        for text in [
            "",
            "dynphrase v2\nname r\nwords 3\nstates 1\na>$\n",
            "dynphrase v1\nname r\nwords 64\nstates 1\na>$ ab>$\n",
            "dynphrase v1\nname r\nwords 64\nstates 1\na>0 b>$\n",
            "dynphrase v1\nname r\nwords 64\nstates 1\na>$ >$\n",
            "dynphrase v1\nname r\nwords 64\nstates 1\na>$ B>$\n",
            "dynphrase v1\nname r\nwords 64\nstates 2\na>$ b>$\n",
            "dynphrase v1\nname r\nwords 64\nstates 1\na>$ b>7\n",
        ] {
            assert!(
                matches!(Model::parse(text), Err(ModelError::Invalid(_))),
                "{text:?}"
            );
        }
        assert_eq!(
            Model::parse("dynphrase v1\nname r\nwords 63\nstates 1\na>$ b>$\n").unwrap_err(),
            ModelError::InsufficientCapacity
        );
        assert!(Model::parse("dynphrase v1\nname r\nwords 64\nstates 1\na>$ b>$\n").is_ok());
    }

    #[test]
    fn mix_is_a_bijection_on_samples() {
        let mut state = 1u64;
        for value in [0, 1, 2, u64::MAX, 1 << 63] {
            assert_eq!(unmix(mix(value)), value);
        }
        for _ in 0..100_000 {
            state = state
                .wrapping_mul(6364136223846793005)
                .wrapping_add(1442695040888963407);
            assert_eq!(unmix(mix(state)), state);
            assert_eq!(mix(unmix(state)), state);
        }
        assert_ne!(mix(0), mix(1));
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

    fn check_model(source: &str) {
        let model = Model::parse(source).unwrap();
        assert_eq!(model.words(), 3);
        for value in edge_values() {
            let phrase = model.encode(value);
            assert_eq!(model.decode(&phrase), Some(value), "{phrase}");
            for invalid in [
                format!(" {phrase}"),
                format!("{phrase} "),
                phrase.replacen(' ', "  ", 1),
                phrase.replacen(' ', "\t", 1),
                phrase.to_uppercase(),
                format!("{phrase} {}", phrase.split(' ').next().unwrap()),
                phrase.replacen(' ', "", 1),
                String::new(),
            ] {
                assert_eq!(model.decode(&invalid), None, "{invalid:?}");
            }
            for (end, _) in phrase.char_indices().skip(1) {
                assert_eq!(model.decode(&phrase[..end]), None);
            }
        }
        // Largest syntactically valid phrase is out of u64 range unless W^3 == 2^64.
        let top = model.unrank_word(model.word_count() - 1).unwrap();
        assert_eq!(model.decode(&[top.as_str(); 3].join(" ")), None);
        let mut seen = HashSet::new();
        let mut state = 0x9e37_79b9_7f4a_7c15u64;
        for _ in 0..100_000 {
            state = state
                .wrapping_mul(6364136223846793005)
                .wrapping_add(1442695040888963407);
            let phrase = model.encode(state);
            assert_eq!(model.decode(&phrase), Some(state));
            assert!(seen.insert(phrase));
        }
    }

    #[test]
    fn en_unique_roundtrips() {
        check_model(models::EN_UNIQUE);
    }

    #[test]
    fn en_fineweb_roundtrips() {
        check_model(models::EN_FINEWEB);
    }

    #[test]
    fn tr_fineweb_roundtrips_and_unicode() {
        check_model(models::TR_FINEWEB);
        let model = Model::parse(models::TR_FINEWEB).unwrap();
        let phrases: Vec<String> = (0..2000u64)
            .map(|index| model.encode(index.wrapping_mul(0x9e37_79b9_7f4a_7c15)))
            .collect();
        let sample = phrases
            .iter()
            .find(|phrase| {
                phrase
                    .chars()
                    .any(|character| "çğıöşüâîû".contains(character))
            })
            .expect("Turkish letters reachable");
        // NFD (decomposed) spelling of a precomposed letter is not canonical.
        let decomposed = sample
            .replace('ç', "c\u{327}")
            .replace('ş', "s\u{327}")
            .replace('ö', "o\u{308}")
            .replace('ü', "u\u{308}")
            .replace('ğ', "g\u{306}");
        if decomposed != *sample {
            assert_eq!(model.decode(&decomposed), None);
        }
        // Dotless/dotted i are distinct letters, never folded.
        if sample.contains('ı') {
            assert_ne!(
                model.decode(&sample.replace('ı', "i")),
                model.decode(sample)
            );
        }
    }
}
