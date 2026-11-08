//! Synthetic reproducible phrase-v2/v3 comparison.
use readable_hash::{phrase_v2, phrase_v3};
use std::hash::{DefaultHasher, Hasher};
fn show(label: &str, value: u64) {
    let before = phrase_v2::encode_u64(value);
    let after = phrase_v3::encode_u64(value);
    assert_eq!(phrase_v2::decode_u64(&before), Some(value));
    assert_eq!(phrase_v3::decode_u64(&after), Some(value));
    println!("{label}\t{value}\t{before}\t{after}");
}
fn main() {
    for input in [
        "hello",
        "",
        "example",
        "readable hash",
        "The quick brown fox",
    ] {
        let mut hasher = DefaultHasher::new();
        hasher.write(input.as_bytes());
        show(&format!("string:{input:?}"), hasher.finish());
    }
    for value in [0, 1, u64::MAX, 0x243f6a8885a308d3, 0xdeadbeefcafebabe] {
        show(&format!("u64:{value:#x}"), value);
    }
}
