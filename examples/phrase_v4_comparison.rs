//! Synthetic v3/v4 comparison, including DefaultHasher::new().
use readable_hash::{phrase_v3, phrase_v4};
use std::hash::{DefaultHasher, Hasher};

fn show(label: &str, value: u64) {
    let before = phrase_v3::encode_u64(value);
    let after = phrase_v4::encode_u64(value);
    assert_eq!(phrase_v3::decode_u64(&before), Some(value));
    assert_eq!(phrase_v4::decode_u64(&after), Some(value));
    println!("{label}\t{value}\t{before}\t{after}");
}

fn main() {
    for value in [
        0,
        1,
        2,
        42,
        1000,
        123456789,
        i64::MAX as u64,
        1 << 63,
        u64::MAX - 1,
        u64::MAX,
        0x243f6a8885a308d3,
        0xdeadbeefcafebabe,
    ] {
        show(&format!("{value}"), value);
    }
    let mut hasher = DefaultHasher::new();
    hasher.write(b"hello");
    show("hello", hasher.finish());
}
