//! Reversible English-like phrases for 64-bit values: "the bits are in the spaces".
//!
//! [`encode_u64`] turns any `u64` into a short phrase such as `dalmse prospicity cindrable`, and
//! [`decode_u64`] turns the phrase back into the same number. Both are total and exact: every value
//! has one phrase, and every phrase it produces decodes to its value. This is an encoding, not
//! encryption or hashing.
//!
//! A phrase is 11 tokens in 3 or 4 words of 2 to 5 tokens each: a beginning, 0 to 3 middles and an
//! ending. There are exactly 32 such layouts, so the layout stores the low 5 bits. The tokens store
//! the other 59: a beginning takes 7 bits (128 choices), a middle 5 (32) and an ending 5 (32) or 4
//! (16). In 3-word layouts the endings of words 2 and 3 take 4 bits; in 4-word layouts every ending
//! does. Every layout is then exactly 64 bits.
//!
//! Each middle and ending table depends on the previous token. In every context the middles and
//! endings together are prefix-free, and no token is shorter than 2 letters, so the decoder finds
//! every token boundary, and with it the layout, from the letters alone. Every word has a vowel
//! (a, e, i, o, u or y): a beginning without one is always followed by a token with one.
//!
//! The tables are generated from an English word list by `models/compile_phrase.py` (format id
//! `phrase-v5`). Changing them changes every phrase, so treat them as a stable format.
//!
//! ```
//! let phrase = readable_hash::phrase::encode_u64(0x243f6a8885a308d3);
//! assert_eq!(phrase, "dalmse prospicity cindrable");
//! assert_eq!(readable_hash::phrase::decode_u64(&phrase), Some(0x243f6a8885a308d3));
//! ```
use crate::phrase_data as data;
use std::sync::OnceLock;

/// Word lengths in tokens (0 = no word), in the order of their 5-bit index: sorted lexicographically.
const LAYOUTS: [[u8; 4]; 32] = [
    [2, 2, 2, 5],
    [2, 2, 3, 4],
    [2, 2, 4, 3],
    [2, 2, 5, 2],
    [2, 3, 2, 4],
    [2, 3, 3, 3],
    [2, 3, 4, 2],
    [2, 4, 2, 3],
    [2, 4, 3, 2],
    [2, 4, 5, 0],
    [2, 5, 2, 2],
    [2, 5, 4, 0],
    [3, 2, 2, 4],
    [3, 2, 3, 3],
    [3, 2, 4, 2],
    [3, 3, 2, 3],
    [3, 3, 3, 2],
    [3, 3, 5, 0],
    [3, 4, 2, 2],
    [3, 4, 4, 0],
    [3, 5, 3, 0],
    [4, 2, 2, 3],
    [4, 2, 3, 2],
    [4, 2, 5, 0],
    [4, 3, 2, 2],
    [4, 3, 4, 0],
    [4, 4, 3, 0],
    [4, 5, 2, 0],
    [5, 2, 2, 2],
    [5, 2, 4, 0],
    [5, 3, 3, 0],
    [5, 4, 2, 0],
];
const MAX_MIDDLES: usize = 3;

fn text(token: u16) -> &'static str {
    data::TOKENS[token as usize]
        .trim_start_matches('^')
        .trim_end_matches('$')
}

fn context(token: u16) -> usize {
    if token < 256 {
        token as usize
    } else {
        token as usize - 256
    }
}

fn word_count(layout: &[u8; 4]) -> usize {
    layout.iter().filter(|&&length| length != 0).count()
}

/// Bits of the ending of word `position`: 4 where the layout has spare bits, otherwise 5.
fn ending_width(words: usize, position: usize) -> u32 {
    if words == 3 && position == 0 { 5 } else { 4 }
}

fn ending_row(token: u16, width: u32) -> &'static [u16] {
    if width == 5 {
        &data::END32[context(token)]
    } else {
        &data::END16[context(token)]
    }
}

fn has_vowel(spelling: &str) -> bool {
    spelling.bytes().any(|byte| b"aeiouy".contains(&byte))
}

fn validate() {
    static VALID: OnceLock<()> = OnceLock::new();
    VALID.get_or_init(|| {
        fn prefix_free(texts: &[&str]) -> bool {
            texts.iter().enumerate().all(|(index, first)| {
                texts[index + 1..]
                    .iter()
                    .all(|second| !first.starts_with(second) && !second.starts_with(first))
            })
        }
        let plain = |token: &u16| {
            let spelling = text(*token);
            spelling.len() >= 2 && spelling.bytes().all(|byte| byte.is_ascii_lowercase())
        };
        assert!(
            data::BEGIN
                .iter()
                .all(|&token| token < 256 && plain(&token))
        );
        assert!(prefix_free(&data::BEGIN.map(text)));
        for row in 0..768 {
            let (middles, endings) = (&data::MIDDLE[row], &data::END32[row]);
            assert!(middles.iter().all(|&token| (512..1024).contains(&token)));
            assert!(endings.iter().all(|&token| (256..512).contains(&token)));
            assert!(middles.iter().chain(endings).all(plain));
            assert_eq!(data::END16[row], endings[..16]);
            let union: Vec<&str> = middles
                .iter()
                .chain(endings)
                .map(|&token| text(token))
                .collect();
            assert!(
                prefix_free(&union),
                "context {row}: middles and endings overlap"
            );
            // Every word needs a vowel: after a beginning without one (rows 0-255 follow beginnings),
            // every middle and ending has one.
            if row < 256 && !has_vowel(text(row as u16)) {
                assert!(union.iter().all(|piece| has_vowel(piece)), "context {row}");
            }
        }
    });
}

/// Encode least-significant bits first: the layout, then each word's tokens left to right.
pub fn encode_u64(mut value: u64) -> String {
    validate();
    let layout = &LAYOUTS[(value & 31) as usize];
    value >>= 5;
    let words = word_count(layout);
    let mut phrase = String::new();
    for (position, &length) in layout[..words].iter().enumerate() {
        if position != 0 {
            phrase.push(' ');
        }
        let mut token = data::BEGIN[(value & 127) as usize];
        value >>= 7;
        phrase.push_str(text(token));
        for _ in 2..length {
            token = data::MIDDLE[context(token)][(value & 31) as usize];
            value >>= 5;
            phrase.push_str(text(token));
        }
        let width = ending_width(words, position);
        token = ending_row(token, width)[(value & ((1 << width) - 1)) as usize];
        value >>= width;
        phrase.push_str(text(token));
    }
    debug_assert_eq!(value, 0);
    phrase
}

/// The one token in `row` that `remaining` starts with (rows are prefix-free), and its index.
fn parse(remaining: &mut &str, row: &[u16]) -> Option<(u64, u16)> {
    let (digit, &token) = row
        .iter()
        .enumerate()
        .find(|(_, token)| remaining.starts_with(text(**token)))?;
    *remaining = &remaining[text(token).len()..];
    Some((digit as u64, token))
}

/// Decode only canonical phrases: 3 or 4 words separated by single spaces, lowercase, nothing else.
pub fn decode_u64(phrase: &str) -> Option<u64> {
    validate();
    let words: Vec<&str> = phrase.split(' ').collect();
    if !(3..=4).contains(&words.len()) {
        return None;
    }
    let mut lengths = [0u8; 4];
    let mut value = 0u64;
    let mut offset = 5;
    let mut push = |digit: u64, width: u32| {
        value |= digit << offset;
        offset += width;
    };
    for (position, word) in words.iter().enumerate() {
        let mut remaining = *word;
        let (digit, mut token) = parse(&mut remaining, &data::BEGIN)?;
        push(digit, 7);
        let width = ending_width(words.len(), position);
        let mut middles = 0;
        // Middles and endings are prefix-free together, so at most one of them matches here.
        loop {
            if let Some((digit, _)) = parse(&mut remaining, ending_row(token, width)) {
                push(digit, width);
                break;
            }
            if middles == MAX_MIDDLES {
                return None;
            }
            let (digit, next) = parse(&mut remaining, &data::MIDDLE[context(token)])?;
            push(digit, 5);
            token = next;
            middles += 1;
        }
        if !remaining.is_empty() {
            return None;
        }
        lengths[position] = middles as u8 + 2;
    }
    let layout = LAYOUTS.iter().position(|layout| *layout == lengths)?;
    debug_assert_eq!(offset, 64);
    Some(value | layout as u64)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::HashSet;

    #[test]
    fn layouts_are_every_split_of_eleven_tokens() {
        let mut expected = Vec::new();
        for words in 1..=4u32 {
            for code in 0..4u32.pow(words) {
                let lengths: Vec<u8> = (0..words)
                    .map(|index| (code / 4u32.pow(index) % 4) as u8 + 2)
                    .rev()
                    .collect();
                if lengths.iter().map(|&length| u32::from(length)).sum::<u32>() == 11 {
                    let mut layout = [0u8; 4];
                    layout[..lengths.len()].copy_from_slice(&lengths);
                    expected.push(layout);
                }
            }
        }
        expected.sort();
        assert_eq!(expected, LAYOUTS);
        for layout in &LAYOUTS {
            let words = word_count(layout);
            let bits: u32 = 5 + layout[..words]
                .iter()
                .enumerate()
                .map(|(position, &length)| {
                    7 + 5 * (u32::from(length) - 2) + ending_width(words, position)
                })
                .sum::<u32>();
            assert_eq!(bits, 64, "{layout:?}");
        }
    }

    #[test]
    fn golden_and_canonical() {
        // Generated by models/compile_phrase.py's reference encoder.
        for (value, expected) in [
            (0x0, "redes redes redes reversitation"),
            (0x1, "redes redes reverted reversible"),
            (0x2, "redes redes reversible reverted"),
            (0x1f, "reversitation reversible redes"),
            (0x20, "unable redes redes reversitation"),
            (0x2a, "unable reversitation redes redes"),
            (0x3e8, "anent reversible reverted redes"),
            (0x75bcd15, "tumenald unable redes reverted"),
            (0x7fffffffffffffff, "jabaltiddes jabaltous jaing"),
            (0x8000000000000000, "redes redes redes reversitake"),
            (0xfffffffffffffffe, "jabaltiddes jabanus jabanus"),
            (0xffffffffffffffff, "jabaltiddes jabaltous jaic"),
            (0x243f6a8885a308d3, "dalmse prospicity cindrable"),
            (0xdeadbeefcafebabe, "ceiloparms atkits taboes"),
        ] {
            assert_eq!(encode_u64(value), expected, "{value:#x}");
            assert_eq!(decode_u64(expected), Some(value), "{expected}");
        }
        let phrase = encode_u64(123456789);
        for invalid in [
            format!(" {phrase}"),
            format!("{phrase} "),
            phrase.replace(' ', "  "),
            phrase.replace(' ', "\t"),
            phrase.to_uppercase(),
            format!("{phrase}x"),
            format!("{phrase} extra"),
            format!("{phrase} {phrase}"),
            phrase.replacen(' ', "", 1),
            "é".to_owned(),
            String::new(),
        ] {
            assert_eq!(decode_u64(&invalid), None, "{invalid:?}");
        }
        for end in 0..phrase.len() {
            assert_eq!(decode_u64(&phrase[..end]), None);
        }
    }

    #[test]
    fn distinct_roundtrips_reach_every_layout() {
        let mut state = 0x243f6a8885a308d3u64;
        let mut phrases = HashSet::new();
        let mut layouts = HashSet::new();
        for _ in 0..100_000 {
            state = state
                .wrapping_mul(6364136223846793005)
                .wrapping_add(1442695040888963407);
            let phrase = encode_u64(state);
            assert_eq!(decode_u64(&phrase), Some(state), "{phrase}");
            assert!(phrases.insert(phrase.clone()));
            let lengths: Vec<usize> = phrase.split(' ').map(str::len).collect();
            assert!(lengths.iter().all(|&letters| letters >= 4), "{phrase}");
            assert!(phrase.split(' ').all(has_vowel), "{phrase}");
            layouts.insert(state & 31);
        }
        assert_eq!(layouts.len(), 32);
    }

    #[test]
    fn every_bit_of_every_layout_roundtrips() {
        for layout in 0..32u64 {
            for bit in 5..64 {
                for base in [0, !31] {
                    let value = (base ^ (1 << bit)) | layout;
                    let phrase = encode_u64(value);
                    assert_eq!(decode_u64(&phrase), Some(value), "{phrase}");
                }
            }
        }
    }
}
