//! Reversible three-word phrase format, independent of the v1 word format.
//!
//! This experimental format uses the frozen generated phrase-v2 tables.
//! Digits are taken least-significant first; the format is independent of v1.
//! This encoding is not encryption or a hash of arbitrary input.

use crate::phrase_v2_data;

/// Encode using the frozen experimental phrase-v2 model.
pub fn encode_u64(value: u64) -> String {
    frozen_model().encode_u64(value)
}

/// Decode a canonical phrase emitted by the frozen experimental model.
pub fn decode_u64(phrase: &str) -> Option<u64> {
    frozen_model().decode_u64(phrase)
}

fn frozen_model() -> &'static Model<'static> {
    static MODEL: std::sync::OnceLock<Model<'static>> = std::sync::OnceLock::new();
    MODEL.get_or_init(|| {
        Model::new(
            &phrase_v2_data::TOKENS,
            &phrase_v2_data::BEGIN,
            &phrase_v2_data::MIDDLE16,
            &phrase_v2_data::MIDDLE8,
            &phrase_v2_data::END128,
        )
        .expect("invalid generated phrase-v2 model")
    })
}

/// Ordered token tables for phrase v2. Token IDs 0..256 are beginnings,
/// 256..512 endings, and 512..1024 middles. A beginning choice may also
/// refer to a middle ID. Context rows 0..256 refer to
/// beginning IDs; rows 256..768 refer to middle IDs minus 256. Beginning
/// and ending spellings may carry the conventional `^` and `$` markers.
/// The 8-choice table is explicit, rather than assumed to be a 16-choice prefix.
/// All choices in each row must have distinct, nonempty, prefix-free lowercase
/// ASCII spellings. Only validated models can be used for encoding and decoding.
pub struct Model<'a> {
    tokens: &'a [&'a str; 1024],
    begin: &'a [u16; 128],
    middle16: &'a [[u16; 16]; 768],
    middle8: &'a [[u16; 8]; 768],
    end: &'a [[u16; 128]; 768],
}

impl<'a> Model<'a> {
    /// Validate and construct a phrase model from generated tables.
    pub fn new(
        tokens: &'a [&'a str; 1024],
        begin: &'a [u16; 128],
        middle16: &'a [[u16; 16]; 768],
        middle8: &'a [[u16; 8]; 768],
        end: &'a [[u16; 128]; 768],
    ) -> Option<Self> {
        let model = Self {
            tokens,
            begin,
            middle16,
            middle8,
            end,
        };
        if !begin
            .iter()
            .all(|&token| token < 256 || (512..1024).contains(&token))
            || !model.valid_choices(begin, 0..1024)
        {
            return None;
        }
        for row in 0..768 {
            if !model.valid_choices(&middle16[row], 512..1024)
                || !model.valid_choices(&middle8[row], 512..1024)
                || !model.valid_choices(&end[row], 256..512)
            {
                return None;
            }
        }
        Some(model)
    }

    fn text(&self, token: u16) -> &str {
        self.tokens[token as usize]
            .trim_start_matches('^')
            .trim_end_matches('$')
    }

    fn valid_choices(&self, choices: &[u16], range: std::ops::Range<u16>) -> bool {
        for (index, &token) in choices.iter().enumerate() {
            if !range.contains(&token) {
                return false;
            }
            let spelling = self.text(token);
            if spelling.is_empty() || !spelling.bytes().all(|byte| byte.is_ascii_lowercase()) {
                return false;
            }
            if choices[..index].iter().any(|&other| {
                let other = self.text(other);
                spelling.starts_with(other) || other.starts_with(spelling)
            }) {
                return false;
            }
        }
        true
    }

    fn parse(&self, remaining: &mut &str, choices: &[u16]) -> Option<(usize, u16)> {
        let (digit, &token) = choices
            .iter()
            .enumerate()
            .find(|(_, token)| remaining.starts_with(self.text(**token)))?;
        *remaining = &remaining[self.text(token).len()..];
        Some((digit, token))
    }

    /// Encode a 64-bit value as three lowercase words separated by single spaces.
    /// Digits are extracted least-significant first, in B/M/M/E order. The
    /// second middle has 16 choices in word one and 8 in words two and three.
    pub fn encode_u64(&self, mut value: u64) -> String {
        let mut phrase = String::new();
        for word in 0..3 {
            if word != 0 {
                phrase.push(' ');
            }
            let mut token = self.begin[(value & 127) as usize];
            value >>= 7;
            phrase.push_str(self.text(token));
            token = self.middle16[context(token)][(value & 15) as usize];
            value >>= 4;
            phrase.push_str(self.text(token));
            let width = if word == 0 { 4 } else { 3 };
            let digit = (value & ((1 << width) - 1)) as usize;
            value >>= width;
            token = if word == 0 {
                self.middle16[context(token)][digit]
            } else {
                self.middle8[context(token)][digit]
            };
            phrase.push_str(self.text(token));
            token = self.end[context(token)][(value & 127) as usize];
            value >>= 7;
            phrase.push_str(self.text(token));
        }
        debug_assert_eq!(value, 0);
        phrase
    }

    /// Decode only canonical phrases: exactly three words, with single ASCII
    /// spaces and no leading/trailing whitespace or extra characters.
    pub fn decode_u64(&self, phrase: &str) -> Option<u64> {
        let mut words = phrase.split(' ');
        let mut value = 0u64;
        let mut offset = 0;
        for word in 0..3 {
            let mut remaining = words.next()?;
            let (digit, mut token) = self.parse(&mut remaining, self.begin)?;
            value |= (digit as u64) << offset;
            offset += 7;
            let (digit, next) = self.parse(&mut remaining, &self.middle16[context(token)])?;
            token = next;
            value |= (digit as u64) << offset;
            offset += 4;
            let (digit, next) = if word == 0 {
                self.parse(&mut remaining, &self.middle16[context(token)])?
            } else {
                self.parse(&mut remaining, &self.middle8[context(token)])?
            };
            token = next;
            value |= (digit as u64) << offset;
            offset += if word == 0 { 4 } else { 3 };
            let (digit, _) = self.parse(&mut remaining, &self.end[context(token)])?;
            value |= (digit as u64) << offset;
            offset += 7;
            if !remaining.is_empty() {
                return None;
            }
        }
        if words.next().is_some() {
            return None;
        }
        debug_assert_eq!(offset, 64);
        Some(value)
    }
}

fn context(token: u16) -> usize {
    if token < 256 {
        token as usize
    } else {
        token as usize - 256
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::HashSet;
    use std::hash::{DefaultHasher, Hasher};

    #[test]
    fn production_vectors_and_sample() {
        let mut hasher = DefaultHasher::new();
        hasher.write(b"hello");
        let hello = hasher.finish();
        for (value, expected) in [
            (0, "abbabiable abbalanable abbalanable"),
            (1, "accedaleable abbalanable abbalanable"),
            (u64::MAX, "zywoz zythz zythz"),
            (16350172494705860510, "computeves fervantish tankerton"),
        ] {
            let phrase = encode_u64(value);
            assert_eq!(phrase, expected);
            assert_eq!(decode_u64(&phrase), Some(value));
        }
        assert_eq!(decode_u64(&encode_u64(hello)), Some(hello));
        let mut seen = HashSet::new();
        let mut value = 0x243f6a8885a308d3u64;
        for _ in 0..100_000 {
            value = value
                .wrapping_mul(6364136223846793005)
                .wrapping_add(1442695040888963407);
            let phrase = encode_u64(value);
            assert_eq!(decode_u64(&phrase), Some(value));
            assert!(seen.insert(phrase));
        }
        let phrase = encode_u64(0);
        for invalid in [
            format!(" {phrase}"),
            format!("{phrase} "),
            phrase.replace(' ', "  "),
            phrase.replace(' ', "\t"),
            format!("{phrase}x"),
            phrase.to_uppercase(),
            String::new(),
        ] {
            assert_eq!(decode_u64(&invalid), None);
        }
    }

    fn fixture() -> Model<'static> {
        let tokens = Box::leak(Box::new(std::array::from_fn(|index| {
            let digit = index % 256;
            let spelling = format!(
                "{}{}",
                (b'a' + (digit / 26) as u8) as char,
                (b'a' + (digit % 26) as u8) as char
            );
            &*Box::leak(spelling.into_boxed_str())
        })));
        let begin = Box::leak(Box::new(std::array::from_fn(|index| index as u16)));
        let middle16 = Box::leak(Box::new(
            [[
                512, 513, 514, 515, 516, 517, 518, 519, 520, 521, 522, 523, 524, 525, 526, 527,
            ]; 768],
        ));
        let middle8 = Box::leak(Box::new([[520, 521, 522, 523, 524, 525, 526, 527]; 768]));
        let end = Box::leak(Box::new(
            [std::array::from_fn(|index| 256 + index as u16); 768],
        ));
        Model::new(tokens, begin, middle16, middle8, end).unwrap()
    }

    #[test]
    fn roundtrips_and_frozen_fixture_vectors() {
        let model = fixture();
        for (value, expected) in [
            (0, "aaaaaaaa aaaaaiaa aaaaaiaa"),
            (u64::MAX, "exapapex exapapex exapapex"),
        ] {
            assert_eq!(model.encode_u64(value), expected);
            assert_eq!(model.decode_u64(expected), Some(value));
        }
        let mut seen = HashSet::new();
        let mut state = 0x243f6a8885a308d3u64;
        for _ in 0..100_000 {
            state = state
                .wrapping_mul(6364136223846793005)
                .wrapping_add(1442695040888963407);
            let phrase = model.encode_u64(state);
            assert_eq!(model.decode_u64(&phrase), Some(state));
            assert!(seen.insert(phrase));
        }
    }

    #[test]
    fn rejects_noncanonical_input() {
        let model = fixture();
        let phrase = model.encode_u64(123456789);
        assert_eq!(model.decode_u64(""), None);
        for invalid in [
            format!(" {phrase}"),
            format!("{phrase} "),
            phrase.replace(' ', "  "),
            phrase.replace(' ', "\t"),
            phrase.to_uppercase(),
            format!("{phrase}a"),
            "é".to_owned(),
        ] {
            assert_eq!(model.decode_u64(&invalid), None);
        }
        for end in 0..phrase.len() {
            assert_eq!(model.decode_u64(&phrase[..end]), None);
        }
    }

    #[test]
    fn exhaustive_reduced_bit_analogue() {
        // Context-dependent prefix-free binary rows, four tokens per word.
        let mut paths = HashSet::new();
        for value in 0u16..4096 {
            let mut remaining = value;
            let mut phrase = String::new();
            let mut previous = 0;
            for position in 0..12 {
                if position % 4 == 0 {
                    if position != 0 {
                        phrase.push(' ');
                    }
                    previous = 0;
                }
                let digit = remaining & 1;
                remaining >>= 1;
                let choices = if previous == 0 {
                    ["a", "bc"]
                } else {
                    ["de", "f"]
                };
                phrase.push_str(choices[digit as usize]);
                previous = digit;
            }
            let mut reconstructed = 0u16;
            for (word_index, word) in phrase.split(' ').enumerate() {
                let mut rest = word;
                let mut previous = 0;
                for position in 0..4 {
                    let choices = if previous == 0 {
                        ["a", "bc"]
                    } else {
                        ["de", "f"]
                    };
                    let digit = choices
                        .iter()
                        .position(|choice| rest.starts_with(choice))
                        .unwrap();
                    rest = &rest[choices[digit].len()..];
                    reconstructed |= (digit as u16) << (word_index * 4 + position);
                    previous = digit as u16;
                }
                assert!(rest.is_empty());
            }
            assert_eq!(reconstructed, value);
            assert!(paths.insert(phrase));
        }
    }
}
