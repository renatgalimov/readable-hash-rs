//! Length-minimized (lenmin v1) comparison against phrase v4 and dyn v1.
//!
//! Prints CSV to stdout; every encoding is decoded and asserted. `--sample N`
//! prints a deterministic LCG sample (seed 99) as TSV for the Python
//! cross-check. DefaultHasher output is not stable across Rust versions, so
//! those rows are illustrative only.
use readable_hash::phrase_dyn;
use readable_hash::phrase_lenmin::{self, mix, unmix};
use readable_hash::phrase_v4;
use std::hash::{DefaultHasher, Hasher};
use std::time::Instant;

fn inputs() -> Vec<(String, u64)> {
    let mut rows: Vec<(String, u64)> = [
        0,
        1,
        2,
        3,
        42,
        255,
        256,
        1000,
        65_535,
        123_456_789,
        u32::MAX as u64,
        1 << 32,
        (1 << 63) - 1,
        1 << 63,
        u64::MAX - 1,
        u64::MAX,
        0x243f_6a88_85a3_08d3,
        0xdead_beef_cafe_babe,
        0x5555_5555_5555_5555,
        0xaaaa_aaaa_aaaa_aaaa,
        0x0f0f_0f0f_0f0f_0f0f,
        0xf0f0_f0f0_f0f0_f0f0,
        0x00ff_00ff_00ff_00ff,
        0xff00_ff00_ff00_ff00,
        0x0101_0101_0101_0101,
        0x8000_0000_0000_0001,
        0x0000_ffff_ffff_0000,
        0x1234_5678_9abc_def0,
    ]
    .into_iter()
    .map(|value| (format!("fixed:{value:#x}"), value))
    .collect();
    for shift in [8, 16, 24, 40, 48, 56] {
        rows.push((format!("pow2:{shift}"), 1u64 << shift));
    }
    let mut state = 0x853c_49e6_748f_ea9bu64;
    for index in 0..24 {
        state = state
            .wrapping_mul(6364136223846793005)
            .wrapping_add(1442695040888963407);
        rows.push((format!("lcg:{index}"), state));
    }
    for text in [
        "hello",
        "readable",
        "example",
        "readable hash",
        "hello world",
        "readable-hash-rs",
    ] {
        let mut hasher = DefaultHasher::new();
        hasher.write(text.as_bytes());
        rows.push((format!("defaulthasher:{text}"), hasher.finish()));
    }
    rows
}

fn quote(field: &str) -> String {
    format!("\"{}\"", field.replace('"', "\"\""))
}

fn main() {
    let lenmin = phrase_lenmin::Model::parse(phrase_lenmin::models::EN_UNIQUE).unwrap();
    let dyn_model = phrase_dyn::Model::parse(phrase_dyn::models::EN_UNIQUE).unwrap();
    let arguments: Vec<String> = std::env::args().collect();
    if arguments.len() == 3 && arguments[1] == "--sample" {
        let count: usize = arguments[2].parse().unwrap();
        let mut state = 99u64;
        for _ in 0..count {
            state = state
                .wrapping_mul(6364136223846793005)
                .wrapping_add(1442695040888963407);
            println!(
                "{state}\t{}\t{}",
                lenmin.encode(state),
                lenmin.encode(mix(state))
            );
        }
        return;
    }
    println!("label,value_hex,value,v4,dyn_en_unique,lenmin_raw,lenmin_mix_v1");
    for (label, value) in inputs() {
        let v4 = phrase_v4::encode_u64(value);
        assert_eq!(phrase_v4::decode_u64(&v4), Some(value));
        let dynamic = dyn_model.encode(value);
        assert_eq!(dyn_model.decode(&dynamic), Some(value));
        let raw = lenmin.encode(value);
        assert_eq!(lenmin.decode(&raw), Some(value));
        let mixed = lenmin.encode(mix(value));
        assert_eq!(lenmin.decode(&mixed).map(unmix), Some(value));
        println!(
            "{},{value:#018x},{value},{},{},{},{}",
            quote(&label),
            quote(&v4),
            quote(&dynamic),
            quote(&raw),
            quote(&mixed)
        );
    }
    let started = Instant::now();
    let (mut total, mut longest) = (0usize, 0usize);
    let mut state = 7u64;
    for _ in 0..200_000 {
        state = state
            .wrapping_mul(6364136223846793005)
            .wrapping_add(1442695040888963407);
        let phrase = lenmin.encode(state);
        total += phrase.chars().count();
        longest = longest.max(phrase.chars().count());
        assert_eq!(lenmin.decode(&phrase), Some(state));
    }
    eprintln!(
        "timing lenmin ({}): 200000 encode+decode in {:.3}s, mean {:.2} chars, max {longest}",
        lenmin.name(),
        started.elapsed().as_secs_f64(),
        total as f64 / 200_000.0
    );
}
