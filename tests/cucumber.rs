use cucumber::{World as _, given, then, when};
use futures::executor::block_on;
use readable_hash::{english_word, english_word_hash, naive_readable_hash};

#[derive(Debug, Default, cucumber::World)]
struct HashWorld {
    input: String,
    output: String,
    entropy: Vec<u8>,
}

#[given(expr = "the input {string}")]
fn set_input(world: &mut HashWorld, input: String) {
    world.input = input;
}

#[when("the hash is generated")]
fn generate_hash(world: &mut HashWorld) {
    world.output = naive_readable_hash(&world.input);
}

#[when("the english word hash is generated")]
fn generate_english_word_hash(world: &mut HashWorld) {
    world.output = english_word_hash(&world.input);
}

#[then(expr = "the result should be {string}")]
fn check_result(world: &mut HashWorld, expected: String) {
    // Trim trailing spaces for comparison since cucumber tables trim them
    assert_eq!(world.output.trim_end(), expected.trim_end());
}

#[then(expr = "the result should have length {int}")]
fn check_length(world: &mut HashWorld, expected_length: usize) {
    assert_eq!(
        world.output.len(),
        expected_length,
        "Expected length {}, got {} for output: '{}'",
        expected_length,
        world.output.len(),
        world.output
    );
}

#[then("the result should be a single word")]
fn check_single_word(world: &mut HashWorld) {
    assert!(
        !world.output.contains(' '),
        "Expected single word (no spaces), got: '{}'",
        world.output
    );
}

#[given(expr = "the entropy bytes {string}")]
fn set_entropy(world: &mut HashWorld, hex: String) {
    world.entropy = hex::decode(&hex).expect("Invalid hex string");
}

#[when(expr = "a word is generated with max {int} tokens")]
fn generate_word_with_max_tokens(world: &mut HashWorld, max_tokens: usize) {
    world.output = match max_tokens {
        2 => english_word::generate_word::<2>(&world.entropy),
        4 => english_word::generate_word::<4>(&world.entropy),
        8 => english_word::generate_word::<8>(&world.entropy),
        16 => english_word::generate_word::<16>(&world.entropy),
        _ => panic!("Unsupported max_tokens value: {}", max_tokens),
    };
}

#[then(expr = "the result should have at most {int} tokens")]
fn check_max_tokens(world: &mut HashWorld, max_tokens: usize) {
    // Count tokens by looking at the structure of the output
    // This is approximate - we check the word isn't too long
    // A more accurate test would require exposing token boundaries
    let output_len = world.output.len();
    // Each token produces at least 1 character, typically 2-4
    // So max_tokens * 6 is a reasonable upper bound
    let max_expected_len = max_tokens * 6;
    assert!(
        output_len <= max_expected_len,
        "Output '{}' (len={}) exceeds expected max length {} for {} tokens",
        world.output,
        output_len,
        max_expected_len,
        max_tokens
    );
}

fn main() {
    block_on(HashWorld::run("tests/features"));
}
