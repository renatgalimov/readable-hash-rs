use cucumber::{World as _, given, then, when};
use futures::executor::block_on;
use readable_hash::readable_hash;

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
    world.output = readable_hash(&world.input);
}

#[then(expr = "the result should be {string}")]
fn check_result(world: &mut HashWorld, expected: String) {
    assert_eq!(world.output, expected);
}

fn main() {
    block_on(HashWorld::run("tests/features"));
}
