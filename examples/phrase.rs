//! Turn numbers into phrases and back.
//!
//! `cargo run --example phrase` prints a few fixed values;
//! `cargo run --example phrase -- 12345 0xdeadbeef` encodes your own (decimal or 0x-hex);
//! `cargo run --example phrase -- "gungwe antabaka yeeljila"` decodes a phrase.
use readable_hash::{decode_u64, encode_u64};

fn parse(argument: &str) -> Option<u64> {
    match argument.strip_prefix("0x") {
        Some(hex) => u64::from_str_radix(hex, 16).ok(),
        None => argument.parse().ok(),
    }
}

fn main() {
    let arguments: Vec<String> = std::env::args().skip(1).collect();
    if arguments.is_empty() {
        for value in [0u64, 1, 42, 123_456_789, 0x243f_6a88_85a3_08d3, u64::MAX] {
            let phrase = encode_u64(value);
            assert_eq!(decode_u64(&phrase), Some(value));
            println!("{value:#018x}  {phrase}");
        }
        return;
    }
    for argument in arguments {
        match parse(&argument) {
            Some(value) => println!("{value:#018x}  {}", encode_u64(value)),
            None => match decode_u64(&argument) {
                Some(value) => println!("{argument}  {value:#018x} ({value})"),
                None => println!("{argument}  not a phrase"),
            },
        }
    }
}
