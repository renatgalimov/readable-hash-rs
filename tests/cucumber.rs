use cucumber::{World as _, given, then, when};
use futures::executor::block_on;
#[cfg(feature = "shake256")]
use readable_hash::Shake256Hasher;
use readable_hash::{SliceReader, StdHasher, english_word, english_word_hash, naive_readable_hash};

#[derive(Debug, Default, Clone, Copy, PartialEq)]
enum HasherType {
    #[default]
    Std,
    #[cfg(feature = "shake256")]
    Shake256,
}

#[derive(Debug, Default, cucumber::World)]
struct HashWorld {
    input: String,
    output: String,
    entropy: Vec<u8>,
    hasher_type: HasherType,
}

#[given(expr = "the input {string}")]
fn set_input(world: &mut HashWorld, input: String) {
    world.input = input;
}

#[given("using the std hasher")]
fn use_std_hasher(world: &mut HashWorld) {
    world.hasher_type = HasherType::Std;
}

#[cfg(feature = "shake256")]
#[given("using the shake256 hasher")]
fn use_shake256_hasher(world: &mut HashWorld) {
    world.hasher_type = HasherType::Shake256;
}

#[when("the hash is generated")]
fn generate_hash(world: &mut HashWorld) {
    world.output = match world.hasher_type {
        HasherType::Std => naive_readable_hash::<StdHasher, _>(&world.input),
        #[cfg(feature = "shake256")]
        HasherType::Shake256 => naive_readable_hash::<Shake256Hasher, _>(&world.input),
    };
}

#[when("the english word hash is generated")]
fn generate_english_word_hash(world: &mut HashWorld) {
    world.output = match world.hasher_type {
        HasherType::Std => english_word_hash::<StdHasher, _>(&world.input),
        #[cfg(feature = "shake256")]
        HasherType::Shake256 => english_word_hash::<Shake256Hasher, _>(&world.input),
    };
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

#[when("a word is generated from the entropy")]
fn generate_word_from_entropy(world: &mut HashWorld) {
    let mut reader = SliceReader::new(&world.entropy);
    world.output = english_word::generate_word(&mut reader);
}

fn main() {
    block_on(HashWorld::run("tests/features"));
}
