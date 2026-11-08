//! Experimental bounded, state-dependent grammar ranked by completion counts.
//!
//! Each edge emits one fixed token and changes state. A phrase contains exactly
//! `length` tokens; a state must be accepting after the last token. Choices in
//! each state must be nonempty, whitespace-free and prefix-free. Ordering of
//! states and edges is part of the wire format. Counts use checked `u128`
//! arithmetic, so grammars too large to count are rejected rather than wrapped.

/// A token and the state reached after emitting it.
#[derive(Clone, Debug)]
pub struct Choice {
    pub token: String,
    pub next_state: usize,
}

/// Choices available in one context and whether it can end a phrase.
#[derive(Clone, Debug)]
pub struct State {
    pub accepting: bool,
    pub choices: Vec<Choice>,
}

/// A validated fixed-token-count grammar and its completion-count table.
#[derive(Clone, Debug)]
pub struct Grammar {
    states: Vec<State>,
    start: usize,
    length: usize,
    counts: Vec<Vec<u128>>,
}

/// Invalid grammar, overflow, or input outside the codec's domain.
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum Error {
    InvalidGrammar,
    CountOverflow,
    InsufficientCapacity,
    InvalidPhrase,
    RankOutOfRange,
}

impl Grammar {
    /// Build a bounded grammar. At least 2^64 complete phrases are required.
    pub fn new(states: Vec<State>, start: usize, length: usize) -> Result<Self, Error> {
        if start >= states.len() || length == 0 {
            return Err(Error::InvalidGrammar);
        }
        for state in &states {
            for (index, choice) in state.choices.iter().enumerate() {
                if choice.next_state >= states.len()
                    || choice.token.is_empty()
                    || choice.token.chars().any(char::is_whitespace)
                    || state.choices[..index].iter().any(|other| {
                        other.token.starts_with(&choice.token)
                            || choice.token.starts_with(&other.token)
                    })
                {
                    return Err(Error::InvalidGrammar);
                }
            }
        }
        let mut counts =
            vec![vec![0u128; states.len()]; length.checked_add(1).ok_or(Error::CountOverflow)?];
        for (index, state) in states.iter().enumerate() {
            counts[0][index] = u128::from(state.accepting);
        }
        for remaining in 1..=length {
            for (index, state) in states.iter().enumerate() {
                for choice in &state.choices {
                    counts[remaining][index] = counts[remaining][index]
                        .checked_add(counts[remaining - 1][choice.next_state])
                        .ok_or(Error::CountOverflow)?;
                }
            }
        }
        if counts[length][start] < (1u128 << 64) {
            return Err(Error::InsufficientCapacity);
        }
        Ok(Self {
            states,
            start,
            length,
            counts,
        })
    }

    /// Number of complete phrases, including phrases beyond the u64 domain.
    pub fn capacity(&self) -> u128 {
        self.counts[self.length][self.start]
    }

    /// Encode a u64 using its exact rank, without modulo reduction.
    pub fn encode(&self, value: u64) -> String {
        let mut rank = u128::from(value);
        let mut state = self.start;
        let mut tokens = Vec::with_capacity(self.length);
        for remaining in (1..=self.length).rev() {
            for choice in &self.states[state].choices {
                let completions = self.counts[remaining - 1][choice.next_state];
                if rank < completions {
                    tokens.push(choice.token.as_str());
                    state = choice.next_state;
                    break;
                }
                rank -= completions;
            }
        }
        tokens.join(" ")
    }

    /// Decode a canonical phrase; valid ranks above u64::MAX are rejected.
    pub fn decode(&self, phrase: &str) -> Result<u64, Error> {
        let tokens: Vec<&str> = phrase.split(' ').collect();
        if tokens.len() != self.length {
            return Err(Error::InvalidPhrase);
        }
        let mut rank = 0u128;
        let mut state = self.start;
        for (index, token) in tokens.iter().enumerate() {
            let remaining = self.length - index - 1;
            let mut matched = None;
            for choice in &self.states[state].choices {
                if choice.token == *token {
                    matched = Some(choice.next_state);
                    break;
                }
                rank = rank
                    .checked_add(self.counts[remaining][choice.next_state])
                    .ok_or(Error::CountOverflow)?;
            }
            state = matched.ok_or(Error::InvalidPhrase)?;
        }
        if !self.states[state].accepting {
            return Err(Error::InvalidPhrase);
        }
        u64::try_from(rank).map_err(|_| Error::RankOutOfRange)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::HashSet;

    fn grammar() -> Grammar {
        // Context changes both the tokens and their destinations. The extra
        // branch creates a capacity above 2^64, exercising unused ranks.
        let states = (0..2)
            .map(|state| State {
                accepting: true,
                choices: (0..17)
                    .map(|index| Choice {
                        token: format!("{}{:02}", if state == 0 { "a" } else { "b" }, index),
                        next_state: (state + index) % 2,
                    })
                    .collect(),
            })
            .collect();
        Grammar::new(states, 0, 16).unwrap()
    }

    #[test]
    fn structural_counts_and_prefixes() {
        let grammar = grammar();
        assert_eq!(grammar.capacity(), 17u128.pow(16));
        for state in &grammar.states {
            for (index, choice) in state.choices.iter().enumerate() {
                for other in &state.choices[index + 1..] {
                    assert!(!choice.token.starts_with(&other.token));
                    assert!(!other.token.starts_with(&choice.token));
                }
            }
        }
        assert!(
            grammar
                .encode(0)
                .split(' ')
                .any(|token| token.starts_with('a'))
        );
        assert!(
            grammar
                .encode(u64::MAX)
                .split(' ')
                .any(|token| token.starts_with('b'))
        );
    }

    #[test]
    fn boundaries_random_and_unique() {
        let grammar = grammar();
        let mut seen = HashSet::new();
        let mut value = 0x1234_5678_9abc_def0u64;
        for index in 0..100_000 {
            value = value
                .wrapping_mul(6364136223846793005)
                .wrapping_add(1442695040888963407);
            let phrase = grammar.encode(value);
            assert_eq!(grammar.decode(&phrase), Ok(value), "{index}");
            assert!(seen.insert(phrase));
        }
        for value in [0, 1, u64::MAX - 1, u64::MAX] {
            assert_eq!(grammar.decode(&grammar.encode(value)), Ok(value));
        }
        assert_eq!(grammar.decode(""), Err(Error::InvalidPhrase));
        assert_eq!(
            grammar.decode(&(grammar.encode(0) + " ")),
            Err(Error::InvalidPhrase)
        );
        let outside = std::iter::once("a16")
            .chain(std::iter::repeat_n("a16", 15))
            .collect::<Vec<_>>()
            .join(" ");
        assert_eq!(grammar.decode(&outside), Err(Error::RankOutOfRange));
    }

    #[test]
    fn exhaustive_three_token_suffix() {
        let grammar = grammar();
        let mut phrases = vec![(vec!["a00".to_string(); 13], 0usize)];
        for _ in 0..3 {
            let mut next = Vec::new();
            for (prefix, state) in phrases {
                for choice in &grammar.states[state].choices {
                    let mut tokens = prefix.clone();
                    tokens.push(choice.token.clone());
                    next.push((tokens, choice.next_state));
                }
            }
            phrases = next;
        }
        assert_eq!(phrases.len(), 4913);
        for (rank, (tokens, _)) in phrases.into_iter().enumerate() {
            let phrase = tokens.join(" ");
            assert_eq!(grammar.encode(rank as u64), phrase);
            assert_eq!(grammar.decode(&phrase), Ok(rank as u64));
        }
    }

    #[test]
    fn invalid_grammars_and_overflow() {
        let state = State {
            accepting: true,
            choices: vec![
                Choice {
                    token: "a".into(),
                    next_state: 0,
                },
                Choice {
                    token: "ab".into(),
                    next_state: 0,
                },
            ],
        };
        assert!(matches!(
            Grammar::new(vec![state], 0, 64),
            Err(Error::InvalidGrammar)
        ));
        let state = State {
            accepting: true,
            choices: vec![
                Choice {
                    token: "a".into(),
                    next_state: 0,
                },
                Choice {
                    token: "b".into(),
                    next_state: 0,
                },
            ],
        };
        assert!(matches!(
            Grammar::new(vec![state.clone()], 0, 63),
            Err(Error::InsufficientCapacity)
        ));
        assert!(matches!(
            Grammar::new(vec![state], 0, 128),
            Err(Error::CountOverflow)
        ));
    }
}
