use cucumber::{World as _, given, then, when};
use futures::executor::block_on;
use readable_hash::{english_word_hash, naive_readable_hash};

#[derive(Debug, Default, cucumber::World)]
struct HashWorld {
    input: String,
    output: String,
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

fn main() {
    block_on(HashWorld::run("tests/features"));
}
