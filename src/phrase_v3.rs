//! Experimental English-only reversible three-word 22+21+21-bit format.
//! This is an encoding, not encryption. Incompatible with phrase v2.
use crate::phrase_v3_data as data;
use std::sync::OnceLock;

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
fn validate() {
    static VALID: OnceLock<()> = OnceLock::new();
    VALID.get_or_init(|| {
        fn check(row: &[u16], allowed: impl Fn(u16) -> bool) {
            for (index, &token) in row.iter().enumerate() {
                assert!(allowed(token));
                let spelling = text(token);
                assert!(
                    !spelling.is_empty() && spelling.bytes().all(|byte| byte.is_ascii_lowercase())
                );
                assert!(
                    row[..index]
                        .iter()
                        .all(|&previous| !spelling.starts_with(text(previous))
                            && !text(previous).starts_with(spelling))
                );
            }
        }
        check(&data::BEGIN, |token| {
            token < 256 || (512..1024).contains(&token)
        });
        for row in 0..768 {
            check(&data::MIDDLE32[row], |token| (512..1024).contains(&token));
            check(&data::MIDDLE16[row], |token| (512..1024).contains(&token));
            check(&data::END32[row], |token| (256..512).contains(&token));
            check(&crate::phrase_v4_data::END16[row], |token| {
                (256..512).contains(&token)
            });
        }
    });
}
fn parse(remaining: &mut &str, row: &[u16]) -> Option<(u64, u16)> {
    let (digit, &token) = row
        .iter()
        .enumerate()
        .find(|(_, token)| remaining.starts_with(text(**token)))?;
    *remaining = &remaining[text(token).len()..];
    Some((digit as u64, token))
}
/// Encode the bits least-significant first, resetting context for each word.
pub fn encode_u64(value: u64) -> String {
    encode_layout(value, false)
}
pub(crate) fn encode_layout(mut value: u64, fourth: bool) -> String {
    validate();
    let mut phrase = String::new();
    for word in 0..3 {
        if word != 0 {
            phrase.push(' ');
        }
        let mut token = data::BEGIN[(value & 127) as usize];
        value >>= 7;
        phrase.push_str(text(token));
        token = data::MIDDLE32[context(token)][(value & 31) as usize];
        value >>= 5;
        phrase.push_str(text(token));
        let width = if word == 0 || (fourth && word == 2) {
            5
        } else {
            4
        };
        let digit = (value & ((1 << width) - 1)) as usize;
        value >>= width;
        token = if width == 5 {
            data::MIDDLE32[context(token)][digit]
        } else {
            data::MIDDLE16[context(token)][digit]
        };
        phrase.push_str(text(token));
        let end_width = if fourth && word == 2 { 4 } else { 5 };
        let end_digit = (value & ((1 << end_width) - 1)) as usize;
        token = if end_width == 4 {
            crate::phrase_v4_data::END16[context(token)][end_digit]
        } else {
            data::END32[context(token)][end_digit]
        };
        value >>= end_width;
        phrase.push_str(text(token));
    }
    debug_assert_eq!(value, 0);
    phrase
}
/// Decode only canonical phrases containing exactly three single-space-separated words.
pub fn decode_u64(phrase: &str) -> Option<u64> {
    decode_layout(phrase, false)
}
pub(crate) fn decode_layout(phrase: &str, fourth: bool) -> Option<u64> {
    validate();
    let mut words = phrase.split(' ');
    let mut value = 0u64;
    let mut offset = 0;
    for word in 0..3 {
        let mut remaining = words.next()?;
        let (digit, mut token) = parse(&mut remaining, &data::BEGIN)?;
        value |= digit << offset;
        offset += 7;
        let (digit, next) = parse(&mut remaining, &data::MIDDLE32[context(token)])?;
        token = next;
        value |= digit << offset;
        offset += 5;
        let width = if word == 0 || (fourth && word == 2) {
            5
        } else {
            4
        };
        let (digit, next) = if width == 5 {
            parse(&mut remaining, &data::MIDDLE32[context(token)])?
        } else {
            parse(&mut remaining, &data::MIDDLE16[context(token)])?
        };
        token = next;
        value |= digit << offset;
        offset += width;
        let end_width = if fourth && word == 2 { 4 } else { 5 };
        let (digit, _) = if end_width == 4 {
            parse(
                &mut remaining,
                &crate::phrase_v4_data::END16[context(token)],
            )?
        } else {
            parse(&mut remaining, &data::END32[context(token)])?
        };
        value |= digit << offset;
        offset += end_width;
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

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::HashSet;
    #[test]
    fn allocation_and_roundtrips() {
        assert_eq!(7 + 5 + 5 + 5, 22);
        assert_eq!(7 + 5 + 4 + 5, 21);
        let mut state = 0x243f6a8885a308d3u64;
        let mut seen = HashSet::new();
        for _ in 0..100_000 {
            state = state
                .wrapping_mul(6364136223846793005)
                .wrapping_add(1442695040888963407);
            let phrase = encode_u64(state);
            assert_eq!(decode_u64(&phrase), Some(state));
            assert!(seen.insert(phrase));
        }
        for value in [0, 1, u64::MAX] {
            assert_eq!(decode_u64(&encode_u64(value)), Some(value));
        }
        for (value, expected) in [
            (0, "abandaia abandaal abandaal"),
            (1, "adaiaca abandaal abandaal"),
            (u64::MAX, "woundzz woundruz woundruz"),
            (16350172494705860510, "crazader filianm subtencities"),
        ] {
            assert_eq!(encode_u64(value), expected);
            assert_eq!(decode_u64(expected), Some(value));
        }
        let phrase = encode_u64(123456789);
        for invalid in [
            format!(" {phrase}"),
            format!("{phrase} "),
            phrase.replace(' ', "  "),
            phrase.replace(' ', "\t"),
            phrase.to_uppercase(),
            format!("{phrase}x"),
            "é".to_owned(),
            String::new(),
        ] {
            assert_eq!(decode_u64(&invalid), None);
        }
        for end in 0..phrase.len() {
            assert_eq!(decode_u64(&phrase[..end]), None);
        }
    }
}
