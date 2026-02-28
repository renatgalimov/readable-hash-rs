//! Word generation helpers for readable hashes.
//!
//! Data tables are generated in `english_word_data.rs`.

use crate::ByteReader;
use crate::english_word_data::{
    CONTEXT_LEN, END_CONTEXTS, END_TRANSITION_DATA, END_TRANSITION_INDEX, MIDDLE_CONTEXTS,
    MIDDLE_TRANSITION_DATA, MIDDLE_TRANSITION_INDEX, NONE_TOKEN, PROBABILITY_BITS, PROBABILITY_MAX,
    TOKENS,
};

/// Find token by binary searching cumulative probabilities.
fn find_token(transitions: &[(u16, u32)], value: u32) -> u16 {
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

    fn read_bits(&mut self, bits: usize) -> Option<u32> {
        if bits == 0 || bits > 32 {
            return None;
        }
        if !self.ensure_bits(bits) {
            return None;
        }

        let mut result: u32 = 0;
        for _ in 0..bits {
            let byte_idx = self.bit_pos / 8;
            let bit_idx = self.bit_pos % 8;
            let bit = (self.buffer[byte_idx] >> (7 - bit_idx)) & 1;
            result = (result << 1) | u32::from(bit);
            self.bit_pos += 1;
        }
        Some(result)
    }

    fn has_more_bits(&mut self, bits: usize) -> bool {
        self.ensure_bits(bits)
    }
}

fn build_context(history: &[u16]) -> Vec<u16> {
    let mut context = vec![NONE_TOKEN; CONTEXT_LEN];
    if CONTEXT_LEN == 0 {
        return context;
    }
    let start = history.len().saturating_sub(CONTEXT_LEN);
    let slice = &history[start..];
    let offset = CONTEXT_LEN - slice.len();
    for (index, token) in slice.iter().enumerate() {
        context[offset + index] = *token;
    }
    context
}

fn context_index(contexts: &[[u16; CONTEXT_LEN]], context: &[u16]) -> Option<usize> {
    if CONTEXT_LEN == 0 {
        return Some(0);
    }
    let mut low = 0usize;
    let mut high = contexts.len();
    while low < high {
        let mid = (low + high) / 2;
        let mid_context = &contexts[mid];
        match context.cmp(mid_context) {
            std::cmp::Ordering::Less => high = mid,
            std::cmp::Ordering::Greater => low = mid + 1,
            std::cmp::Ordering::Equal => return Some(mid),
        }
    }
    None
}

fn transitions_for_context<'a>(
    contexts: &[[u16; CONTEXT_LEN]],
    index: &[(u32, u16)],
    data: &'a [(u16, u32)],
    context: &[u16],
) -> Option<&'a [(u16, u32)]> {
    let context_idx = context_index(contexts, context)?;
    let (start, len) = index[context_idx];
    if len == 0 {
        return None;
    }
    let start = start as usize;
    let len = len as usize;
    Some(&data[start..(start + len)])
}

fn scaled_value(value: u32, max_value: u32, target_max: u32) -> u32 {
    if target_max == 0 {
        return 0;
    }
    if max_value == 0 || max_value == target_max {
        return value.min(target_max);
    }
    let scaled = (u64::from(value) * u64::from(target_max)) / u64::from(max_value);
    scaled.min(u64::from(target_max)) as u32
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
    let Some(begin_value) = bit_reader.read_bits(PROBABILITY_BITS as usize) else {
        return String::new();
    };
    let context = build_context(&[]);
    let Some(transitions) = transitions_for_context(
        &MIDDLE_CONTEXTS,
        &MIDDLE_TRANSITION_INDEX,
        &MIDDLE_TRANSITION_DATA,
        &context,
    ) else {
        return String::new();
    };
    let scaled = scaled_value(
        begin_value,
        PROBABILITY_MAX,
        transitions.last().map_or(0, |(_, cumulative)| *cumulative),
    );
    let first_token = find_token(transitions, scaled);
    result.push_str(token_text(first_token));
    let mut history: Vec<u16> = vec![first_token];
    let mut current_len = result.len();

    loop {
        let context = build_context(&history);
        let middle_transitions = transitions_for_context(
            &MIDDLE_CONTEXTS,
            &MIDDLE_TRANSITION_INDEX,
            &MIDDLE_TRANSITION_DATA,
            &context,
        );
        let end_transitions = transitions_for_context(
            &END_CONTEXTS,
            &END_TRANSITION_INDEX,
            &END_TRANSITION_DATA,
            &context,
        );
        let Some(transitions) = middle_transitions else {
            break;
        };

        if let Some(end_transitions) = end_transitions {
            let mut can_reach_target = current_len >= target_len;
            if !can_reach_target {
                for (end_id, _) in end_transitions {
                    if current_len + token_text(*end_id).len() >= target_len {
                        can_reach_target = true;
                        break;
                    }
                }
            }

            if can_reach_target {
                let value = bit_reader.read_bits(PROBABILITY_BITS as usize).unwrap_or(0);
                let scaled = scaled_value(
                    value,
                    PROBABILITY_MAX,
                    end_transitions
                        .last()
                        .map_or(0, |(_, cumulative)| *cumulative),
                );
                let mut end_token = find_token(end_transitions, scaled);
                if current_len + token_text(end_token).len() < target_len {
                    if let Some((end_id, _)) = end_transitions
                        .iter()
                        .find(|(end_id, _)| current_len + token_text(*end_id).len() >= target_len)
                    {
                        end_token = *end_id;
                    } else if let Some((end_id, _)) = end_transitions.last() {
                        end_token = *end_id;
                    }
                }
                result.push_str(token_text(end_token));
                break;
            }
        }

        let Some(value) = bit_reader.read_bits(PROBABILITY_BITS as usize) else {
            break;
        };
        let scaled = scaled_value(
            value,
            PROBABILITY_MAX,
            transitions.last().map_or(0, |(_, cumulative)| *cumulative),
        );
        let next_token = find_token(transitions, scaled);
        result.push_str(token_text(next_token));
        history.push(next_token);
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
    let Some(begin_value) = bit_reader.read_bits(PROBABILITY_BITS as usize) else {
        return String::new();
    };
    let context = build_context(&[]);
    let Some(transitions) = transitions_for_context(
        &MIDDLE_CONTEXTS,
        &MIDDLE_TRANSITION_INDEX,
        &MIDDLE_TRANSITION_DATA,
        &context,
    ) else {
        return String::new();
    };
    let scaled = scaled_value(
        begin_value,
        PROBABILITY_MAX,
        transitions.last().map_or(0, |(_, cumulative)| *cumulative),
    );
    let first_token = find_token(transitions, scaled);
    let mut current_token: Option<u16> = Some(first_token);
    let mut history: Vec<u16> = vec![first_token];
    result.push_str(token_text(first_token));

    // Select middle tokens while we have entropy
    while bit_reader.has_more_bits(PROBABILITY_BITS as usize) {
        if current_token.is_none() {
            break;
        };
        let context = build_context(&history);
        let Some(transitions) = transitions_for_context(
            &MIDDLE_CONTEXTS,
            &MIDDLE_TRANSITION_INDEX,
            &MIDDLE_TRANSITION_DATA,
            &context,
        ) else {
            break;
        };
        let Some(value) = bit_reader.read_bits(PROBABILITY_BITS as usize) else {
            break;
        };
        let scaled = scaled_value(
            value,
            PROBABILITY_MAX,
            transitions.last().map_or(0, |(_, cumulative)| *cumulative),
        );
        let next_token = find_token(transitions, scaled);
        current_token = Some(next_token);
        result.push_str(token_text(next_token));
        history.push(next_token);
    }

    // Select end token using remaining bits or default
    if current_token.is_some() {
        let context = build_context(&history);
        if let Some(end_transitions) = transitions_for_context(
            &END_CONTEXTS,
            &END_TRANSITION_INDEX,
            &END_TRANSITION_DATA,
            &context,
        ) {
            let value = bit_reader.read_bits(PROBABILITY_BITS as usize).unwrap_or(0);
            let scaled = scaled_value(
                value,
                PROBABILITY_MAX,
                end_transitions
                    .last()
                    .map_or(0, |(_, cumulative)| *cumulative),
            );
            let end_token = find_token(end_transitions, scaled);
            result.push_str(token_text(end_token));
        }
    }

    result
}
