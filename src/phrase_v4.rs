//! Experimental English-only reversible 22+21+21-bit phrase format.
//! V4 changes only the third word's second middle and ending tables from v3.
//! This encoding is not encryption and is incompatible with v3.

/// Encode least-significant bits first, resetting context for each word.
pub fn encode_u64(value: u64) -> String {
    crate::phrase_v3::encode_layout(value, true)
}

/// Decode only canonical phrases with exactly three single-space-separated words.
pub fn decode_u64(phrase: &str) -> Option<u64> {
    crate::phrase_v3::decode_layout(phrase, true)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::HashSet;

    #[test]
    fn golden_and_canonical() {
        for (value, expected) in [
            (0, "abandaia abandaal abandaia"),
            (1, "adaiaca abandaal abandaia"),
            (2, "alarbable abandaal abandaia"),
            (42, "exactaca abandaal abandaia"),
            (1000, "shaemada abandaal abandaia"),
            (123456789, "certiwking couchaberal abandaia"),
            (i64::MAX as u64, "woundzz woundruz woundzine"),
            (1 << 63, "abandaia abandaal abandaims"),
            (u64::MAX - 1, "wizzz woundruz woundzy"),
            (u64::MAX, "woundzz woundruz woundzy"),
            (0x243f6a8885a308d3, "orierling chairasseth steinctare"),
            (0xdeadbeefcafebabe, "jerredy favoureth hereivation"),
            (16350172494705860510, "crazader filianm subtencium"),
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
            format!("{phrase} extra"),
            "é".to_owned(),
            String::new(),
        ] {
            assert_eq!(decode_u64(&invalid), None);
        }
        for end in 0..phrase.len() {
            assert_eq!(decode_u64(&phrase[..end]), None);
        }
    }

    #[test]
    fn distinct_roundtrips_and_unchanged_first_words() {
        let mut state = 0x243f6a8885a308d3u64;
        let mut values = HashSet::new();
        let mut phrases = HashSet::new();
        for _ in 0..100_000 {
            state = state
                .wrapping_mul(6364136223846793005)
                .wrapping_add(1442695040888963407);
            assert!(values.insert(state));
            let phrase = encode_u64(state);
            assert_eq!(decode_u64(&phrase), Some(state));
            assert!(phrases.insert(phrase.clone()));
            let old = crate::phrase_v3::encode_u64(state);
            assert_eq!(
                phrase.split(' ').take(2).collect::<Vec<_>>(),
                old.split(' ').take(2).collect::<Vec<_>>()
            );
        }
    }

    #[test]
    fn exhaustive_one_bit_per_token_analogue() {
        // Exercise both choices of each token digit in every word, using the
        // actual layout and tables rather than a separate toy encoder.
        let offsets = [0, 7, 12, 17, 22, 29, 34, 38, 43, 50, 55, 60];
        let mut seen = HashSet::new();
        for pattern in 0..(1u64 << offsets.len()) {
            let mut value = 0;
            for (index, offset) in offsets.iter().enumerate() {
                value |= ((pattern >> index) & 1) << offset;
            }
            let phrase = encode_u64(value);
            assert_eq!(decode_u64(&phrase), Some(value));
            assert!(seen.insert(phrase));
        }
    }
}
