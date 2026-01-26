#![no_main]

use libfuzzer_sys::fuzz_target;
use readable_hash::SliceReader;

fuzz_target!(|entropy_bytes: &[u8]| {
    let mut reader = SliceReader::new(entropy_bytes);
    let _ = readable_hash::english_word::generate_word(&mut reader);
});
