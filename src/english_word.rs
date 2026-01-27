//! Word generation helpers for readable hashes.
//!
//! Data tables are generated in `english_word_data.rs`.

use crate::ByteReader;
use crate::english_word_data::{
    BEGIN_TRANSITIONS, END_TRANSITION_DATA, END_TRANSITION_INDEX, TOKENS, TRANSITION_DATA,
    TRANSITION_INDEX,
};

/// Find token by binary searching cumulative probabilities.
fn find_token(transitions: &[(u16, u8)], value: u8) -> u16 {
    for (token_id, cumulative) in transitions {
        if *cumulative >= value {
            return *token_id;
        }
    }
    transitions.last().map_or(0, |(id, _)| *id)
}

/// Get the text for a token, stripping position markers.
fn token_text(token_id: u16) -> &'static str {
    let token = TOKENS[token_id as usize];
    let without_prefix = token.strip_prefix('^').unwrap_or(token);
    without_prefix.strip_suffix('$').unwrap_or(without_prefix)
}

/// Bit reader that wraps a `ByteReader`, buffering bytes and reading bits.
struct BitReader<'a, R: ByteReader> {
    reader: &'a mut R,
    buffer: Vec<u8>,
    bit_pos: usize,
    exhausted: bool,
}

impl<'a, R: ByteReader> BitReader<'a, R> {
    const fn new(reader: &'a mut R) -> Self {
        Self {
            reader,
            buffer: Vec::new(),
            bit_pos: 0,
            exhausted: false,
        }
    }

    /// Ensure we have at least `bits` available in the buffer.
    fn ensure_bits(&mut self, bits: usize) -> bool {
        if self.exhausted {
            return self.bits_available() >= bits;
        }

        let bytes_needed = (self.bit_pos + bits).div_ceil(8);
        while self.buffer.len() < bytes_needed {
            let mut byte = [0u8; 1];
            if self.reader.read(&mut byte) == 0 {
                self.exhausted = true;
                break;
            }
            self.buffer.push(byte[0]);
        }
        self.bits_available() >= bits
    }

    const fn bits_available(&self) -> usize {
        (self.buffer.len() * 8).saturating_sub(self.bit_pos)
    }

    fn read_u8(&mut self) -> Option<u8> {
        if !self.ensure_bits(8) {
            return None;
        }

        let mut result: u8 = 0;
        for _ in 0..8 {
            let byte_idx = self.bit_pos / 8;
            let bit_idx = self.bit_pos % 8;
            let bit = (self.buffer[byte_idx] >> (7 - bit_idx)) & 1;
            result = (result << 1) | bit;
            self.bit_pos += 1;
        }
        Some(result)
    }

    fn has_more(&mut self) -> bool {
        self.ensure_bits(8)
    }
}

/// Generate an English-like word with a minimum target length.
///
/// The output always ends with an end token. If it cannot exactly match
/// the target length, it will stop at the shortest possible length
/// that is >= `target_len` when such an end token is available.
pub fn generate_word_with_target_len<R: ByteReader>(reader: &mut R, target_len: usize) -> String {
    let mut bit_reader = BitReader::new(reader);
    let mut result = String::new();

    // Select beginning token
    let Some(begin_value) = bit_reader.read_u8() else {
        return String::new();
    };
    let first_token = find_token(&BEGIN_TRANSITIONS, begin_value);
    result.push_str(token_text(first_token));
    let mut current_token = first_token;
    let mut current_len = result.len();

    loop {
        let (end_start, end_len) = END_TRANSITION_INDEX[current_token as usize];
        if end_len > 0 {
            let end_trans =
                &END_TRANSITION_DATA[end_start as usize..(end_start as usize + end_len as usize)];
            let mut can_reach_target = current_len >= target_len;
            if !can_reach_target {
                for (end_id, _) in end_trans {
                    if current_len + token_text(*end_id).len() >= target_len {
                        can_reach_target = true;
                        break;
                    }
                }
            }

            if can_reach_target {
                let value = bit_reader.read_u8().unwrap_or(0);
                let mut end_token = find_token(end_trans, value);
                if current_len + token_text(end_token).len() < target_len {
                    if let Some((end_id, _)) = end_trans
                        .iter()
                        .find(|(end_id, _)| current_len + token_text(*end_id).len() >= target_len)
                    {
                        end_token = *end_id;
                    } else if let Some((end_id, _)) = end_trans.last() {
                        end_token = *end_id;
                    }
                }
                result.push_str(token_text(end_token));
                break;
            }
        }

        let (start, len) = TRANSITION_INDEX[current_token as usize];
        if len == 0 {
            break;
        }
        let Some(value) = bit_reader.read_u8() else {
            break;
        };
        let trans = &TRANSITION_DATA[start as usize..(start as usize + len as usize)];
        let next_token = find_token(trans, value);
        result.push_str(token_text(next_token));
        current_token = next_token;
        current_len = result.len();
    }

    result
}

/// Generate an English-like word from a `ByteReader`.
///
/// Reads bytes from the reader and generates tokens until the reader
/// is exhausted. The word consists of a beginning token, zero or more
/// middle tokens, and an end token.
///
/// # Panics
///
/// This function will not panic under normal usage. Internal assertions
/// are guaranteed by the function's control flow.
pub fn generate_word<R: ByteReader>(reader: &mut R) -> String {
    let mut bit_reader = BitReader::new(reader);
    let mut result = String::new();

    // Select beginning token
    let Some(begin_value) = bit_reader.read_u8() else {
        return String::new();
    };
    let first_token = find_token(&BEGIN_TRANSITIONS, begin_value);
    let mut current_token: Option<u16> = Some(first_token);
    result.push_str(token_text(first_token));

    // Select middle tokens while we have entropy
    while bit_reader.has_more() {
        let Some(current) = current_token else {
            break;
        };
        let (start, len) = TRANSITION_INDEX[current as usize];
        if len == 0 {
            break;
        }
        let Some(value) = bit_reader.read_u8() else {
            break;
        };
        let trans = &TRANSITION_DATA[start as usize..(start as usize + len as usize)];
        let next_token = find_token(trans, value);
        current_token = Some(next_token);
        result.push_str(token_text(next_token));
    }

    // Select end token using remaining bits or default
    if let Some(current) = current_token {
        let (start, len) = END_TRANSITION_INDEX[current as usize];
        if len > 0 {
            let trans = &END_TRANSITION_DATA[start as usize..(start as usize + len as usize)];
            let value = bit_reader.read_u8().unwrap_or(0);
            let end_token = find_token(trans, value);
            result.push_str(token_text(end_token));
        }
    }

    result
}
