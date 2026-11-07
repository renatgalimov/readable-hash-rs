//! Reversible, version 1 encoding. The tables are part of the wire format.
use crate::reversible_v1_data::{BEGIN, END, MIDDLE, TOKENS};

fn text(token: u16) -> &'static str {
    TOKENS[token as usize]
        .trim_start_matches('^')
        .trim_end_matches('$')
}

fn context_index(token: u16) -> usize {
    if token < 256 {
        token as usize
    } else {
        token as usize - 256
    }
}

/// Encode any 64-bit value as one continuous lowercase word using format v1.
/// This is a reversible encoding, not a collision-free hash of arbitrary input.
pub fn encode_u64(value: u64) -> String {
    let mut quotient = value / BEGIN.len() as u64;
    let mut token = BEGIN[(value % BEGIN.len() as u64) as usize];
    let mut result = String::new();
    result.push_str(text(token));
    for _ in 0..11 {
        token = MIDDLE[context_index(token)][(quotient & 31) as usize];
        quotient >>= 5;
        result.push_str(text(token));
    }
    token = END[context_index(token)][quotient as usize];
    result.push_str(text(token));
    result
}

// Reject ambiguity rather than relying on table ordering if tables are ever corrupted.
fn parse_token(remaining: &mut &str, choices: &[u16]) -> Option<(usize, u16)> {
    let mut found = None;
    for (index, &token) in choices.iter().enumerate() {
        if remaining.starts_with(text(token)) {
            if found.is_some() {
                return None;
            }
            found = Some((index, token));
        }
    }
    let (index, token) = found?;
    *remaining = &remaining[text(token).len()..];
    Some((index, token))
}

/// Decode a canonical v1 word, returning None for malformed or out-of-range paths.
pub fn decode_u64(word: &str) -> Option<u64> {
    let mut remaining = word;
    let (begin, mut token) = parse_token(&mut remaining, &BEGIN)?;
    let mut quotient = 0u128;
    for position in 0..11 {
        let (digit, next) = parse_token(&mut remaining, &MIDDLE[context_index(token)])?;
        quotient |= (digit as u128) << (position * 5);
        token = next;
    }
    let (digit, _) = parse_token(&mut remaining, &END[context_index(token)])?;
    if !remaining.is_empty() {
        return None;
    }
    quotient |= (digit as u128) << 55;
    u64::try_from(quotient * BEGIN.len() as u128 + begin as u128).ok()
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::HashSet;

    fn assert_prefix_free(choices: &[u16]) {
        for (index, &token) in choices.iter().enumerate() {
            assert!(!text(token).is_empty());
            assert!(text(token).bytes().all(|byte| byte.is_ascii_lowercase()));
            for (other_index, &other) in choices.iter().enumerate() {
                if index != other_index {
                    assert!(!text(other).starts_with(text(token)));
                }
            }
        }
    }

    #[test]
    fn tables_are_unambiguous_and_complete() {
        assert_eq!(BEGIN.len(), 179);
        assert_prefix_free(&BEGIN);
        for row in MIDDLE {
            assert_eq!(row.len(), 32);
            assert_prefix_free(&row);
        }
        for row in END {
            assert_eq!(row.len(), 16);
            assert_prefix_free(&row);
        }
        let duplicate = text(BEGIN[0]);
        assert!(parse_token(&mut &*duplicate, &[BEGIN[0], BEGIN[0]]).is_none());
    }

    #[test]
    fn edges_and_large_unique_roundtrip() {
        let mut seen = HashSet::new();
        let edges = [0, 1, 178, 179, 180, u64::MAX, u64::MAX - 1, 1 << 63];
        for value in edges {
            assert_eq!(decode_u64(&encode_u64(value)), Some(value));
        }
        let mut state = 0x243f6a8885a308d3u64;
        for _ in 0..100_000 {
            state = state
                .wrapping_mul(6364136223846793005)
                .wrapping_add(1442695040888963407);
            let word = encode_u64(state);
            assert_eq!(decode_u64(&word), Some(state));
            assert!(seen.insert(word));
        }
    }

    #[test]
    fn v1_golden_vectors() {
        for (value, word) in [
            (0, "abandaiacaiacaiacaiacaiaca"),
            (1, "acacaiacaiacaiacaiacaiaca"),
            (179, "abasaiacaiacaiacaiacaiaca"),
            (123456789, "richeleaskablancceaedabca"),
            (u64::MAX, "priggardzamanitirpicylighvid"),
        ] {
            assert_eq!(encode_u64(value), word);
            assert_eq!(decode_u64(word), Some(value));
        }
    }

    #[test]
    fn rejects_invalid_and_overflow_paths() {
        let word = encode_u64(123456);
        assert_eq!(decode_u64(""), None);
        for end in 0..word.len() {
            assert_eq!(decode_u64(&word[..end]), None);
        }
        assert_eq!(decode_u64(&(word.clone() + "a")), None);
        assert_eq!(decode_u64(&word.to_uppercase()), None);
        assert_eq!(decode_u64("é"), None);
        // Construct a syntactically valid but too-large quotient (all digits 31/15).
        let mut token = BEGIN[0];
        let mut overflow = text(token).to_owned();
        for _ in 0..11 {
            token = MIDDLE[context_index(token)][31];
            overflow.push_str(text(token));
        }
        overflow.push_str(text(END[context_index(token)][15]));
        assert_eq!(decode_u64(&overflow), None);
    }

    #[test]
    fn exhaustive_small_radix_analogue() {
        let mut paths = HashSet::new();
        for value in 0u16..=u16::MAX {
            let begin = value % 7;
            let mut quotient = value / 7;
            let mut digits = [0u16; 5];
            for digit in &mut digits {
                *digit = quotient % 8;
                quotient /= 8;
            }
            assert_eq!(quotient, 0);
            let mut decoded = 0u16;
            for digit in digits.iter().rev() {
                decoded = decoded * 8 + digit;
            }
            assert_eq!(decoded * 7 + begin, value);
            assert!(paths.insert((begin, digits)));
        }
    }
}
