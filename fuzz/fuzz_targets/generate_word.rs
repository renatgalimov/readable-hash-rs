#![no_main]

use libfuzzer_sys::fuzz_target;

fuzz_target!(|entropy_bytes: &[u8]| {
    let _ = readable_hash::english_word::generate_word::<16>(entropy_bytes);
});
