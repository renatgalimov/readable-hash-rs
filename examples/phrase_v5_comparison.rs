//! Print phrase v4 and v5 side by side for the same inputs.
//!
//! `cargo run --example phrase_v5_comparison` prints fixed inputs;
//! `cargo run --example phrase_v5_comparison -- --sample N` prints N values from a fixed LCG as TSV.
use readable_hash::{phrase_v4, phrase_v5};

fn main() {
    let args: Vec<String> = std::env::args().collect();
    if let Some(count) = args
        .iter()
        .position(|arg| arg == "--sample")
        .and_then(|index| args.get(index + 1))
        .and_then(|count| count.parse::<usize>().ok())
    {
        let mut state = 0x9e3779b97f4a7c15u64;
        println!("value\tv4\tv5");
        for _ in 0..count {
            state = state
                .wrapping_mul(6364136223846793005)
                .wrapping_add(1442695040888963407);
            let (old, new) = (phrase_v4::encode_u64(state), phrase_v5::encode_u64(state));
            assert_eq!(phrase_v5::decode_u64(&new), Some(state));
            println!("{state:#018x}\t{old}\t{new}");
        }
        return;
    }
    for value in [
        0u64,
        1,
        42,
        1000,
        123456789,
        0x243f6a8885a308d3,
        0xdeadbeefcafebabe,
        u64::MAX,
    ] {
        let (old, new) = (phrase_v4::encode_u64(value), phrase_v5::encode_u64(value));
        assert_eq!(phrase_v5::decode_u64(&new), Some(value));
        println!("{value:#018x}  v4: {old:<40} v5: {new}");
    }
}
