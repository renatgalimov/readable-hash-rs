//! Experimental dyn-v1 comparison against phrase v4 on fixed synthetic inputs.
//!
//! Prints CSV to stdout. Every encoding is decoded and asserted. Hash rows use
//! `DefaultHasher::new()`, `write(bytes)`, `finish()`; DefaultHasher output is
//! not stable across Rust versions, so those rows are illustrative only.
use readable_hash::phrase_dyn::{self, Model, mix, unmix};
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
    let models = [
        (
            "dyn_en_unique",
            Model::parse(phrase_dyn::models::EN_UNIQUE).unwrap(),
        ),
        (
            "dyn_en_fineweb",
            Model::parse(phrase_dyn::models::EN_FINEWEB).unwrap(),
        ),
        (
            "dyn_tr_fineweb",
            Model::parse(phrase_dyn::models::TR_FINEWEB).unwrap(),
        ),
    ];
    let arguments: Vec<String> = std::env::args().collect();
    if arguments.len() == 3 && arguments[1] == "--sample" {
        // Deterministic LCG sample (seed 99), tab-separated, for proxy metrics.
        let count: usize = arguments[2].parse().unwrap();
        let mut state = 99u64;
        for _ in 0..count {
            state = state
                .wrapping_mul(6364136223846793005)
                .wrapping_add(1442695040888963407);
            let mut fields = vec![state.to_string(), phrase_v4::encode_u64(state)];
            for (_, model) in &models {
                fields.push(model.encode(state));
            }
            fields.push(models[0].1.encode(mix(state)));
            println!("{}", fields.join("\t"));
        }
        return;
    }
    let mut header = vec!["label", "value_hex", "value", "v4"];
    for (name, _) in &models {
        header.push(name);
    }
    header.push("dyn_en_unique_mix_v1");
    println!("{}", header.join(","));
    for (label, value) in inputs() {
        let v4 = phrase_v4::encode_u64(value);
        assert_eq!(phrase_v4::decode_u64(&v4), Some(value));
        let mut fields = vec![
            quote(&label),
            format!("{value:#018x}"),
            value.to_string(),
            quote(&v4),
        ];
        for (_, model) in &models {
            let phrase = model.encode(value);
            assert_eq!(model.decode(&phrase), Some(value));
            fields.push(quote(&phrase));
        }
        let mixed = models[0].1.encode(mix(value));
        assert_eq!(models[0].1.decode(&mixed).map(unmix), Some(value));
        fields.push(quote(&mixed));
        println!("{}", fields.join(","));
    }
    for (name, model) in &models {
        let started = Instant::now();
        let mut total = 0usize;
        let mut state = 7u64;
        for _ in 0..200_000 {
            state = state
                .wrapping_mul(6364136223846793005)
                .wrapping_add(1442695040888963407);
            let phrase = model.encode(state);
            total += phrase.len();
            assert_eq!(model.decode(&phrase), Some(state));
        }
        eprintln!(
            "timing {name} ({}): 200000 encode+decode in {:.3}s, mean {:.2} bytes, W={}",
            model.name(),
            started.elapsed().as_secs_f64(),
            total as f64 / 200_000.0,
            model.word_count()
        );
    }
}
