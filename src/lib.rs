//! Generate human-readable strings from SHA-256 hashes.

use sha2::{Digest, Sha256};
use sha3::Shake256;
use sha3::digest::{ExtendableOutput, Update as XofUpdate, XofReader};

mod english_word;

/// Syllables used for obfuscating lowercase words.
pub(crate) const SYLLABLES: [&str; 256] = [
    "plac", "most ", "sam", "ke", "uth", "arl ", "het", "giv", "fa", "first ", "own ", "li", "van",
    "form ", "pres", "ond", "men ", "bef", "old ", "agr", "must ", "two ", "ight ", "mak", "cons",
    "nat", "den", "rem", "inst", "eb", "itt", "iss ", "tak", "ars", "ap", "app", "iz", "wher",
    "ec", "mad", "cont", "pe", "such ", "lik", "ung", "rec", "gen", "now ", "how ", "urs", "wa",
    "ver ", "than ", "don", "com", "mo", "ught ", "pa", "min", "vi", "comm", "sho", "thes",
    "ents ", "then ", "aft", "fe", "ek", "ha", "ins ", "ep", "ich", "acc", "elf", "ans", "can",
    "ass", "att", "ni", "ex", "work ", "par", "ef", "te", "part ", "ho", "onl", "des", "vo", "tim",
    "ib", "lo", "has", "tho", "proj", "ert", "gre", "ord", "off ", "stat ", "what ", "ort", "der",
    "eg", "gut", "ach", "art ", "si", "ett ", "ern ", "als", "enb", "bo", "ud", "ys", "them ",
    "som", "mor", "act", "unt", "who ", "ac", "ak", "ik", "ish ", "ast ", "when ", "erg", "po",
    "ne", "ard ", "will ", "go", "ugh ", "ro", "um", "da", "ens", "ow", "ja", "my", "ind", "ok",
    "op", "wo", "anc", "ill", "abl", "ther", "fo", "she ", "av", "him ", "ot", "oth", "ig", "ov",
    "its", "ell", "wer", "enc", "ma", "man ", "di", "od", "end ", "do", "up", "re", "no", "im",
    "le", "ab", "om", "sa", "ul", "ant ", "co", "if", "uld ", "ist ", "hav", "ons ", "la", "we",
    "from ", "me", "had ", "but ", "her ", "which ", "so", "ag", "int", "se", "est", "ol", "os",
    "qu", "un", "this ", "ev", "ect ", "ers", "iv", "em", "not ", "am", "by", "ess", "und", "ad",
    "il", "his", "ir", "all ", "for", "was ", "id", "de", "with ", "et", "that ", "be", "ut", "ic",
    "us", "el", "ur", "he", "ent ", "as", "or", "al", "ar", "is", "an", "u", "ing ", "at", "it",
    "es", "to", "and ", "en", "on", "of", "ed ", "o", "in", "er", "i", "a", "y", "the ", "e",
];

/// Generates a SHA-256 hash and returns it as a sentence in a made-up language.
///
/// # Examples
///
/// ```rust
/// use readable_hash::naive_readable_hash;
///
/// let sentence = naive_readable_hash("hello");
/// assert_eq!(
///     sentence,
///     "ungtoattmeertant dipresecorvisuch osfrom usellremight itthasiss upfeprojthem uthver off abljahim iz",
/// );
/// ```
pub fn naive_readable_hash(input: &str) -> String {
    let mut hasher = Sha256::new();
    Digest::update(&mut hasher, input.as_bytes());
    let result = hasher.finalize();
    result
        .iter()
        .map(|b| SYLLABLES[*b as usize])
        .collect::<String>()
}

/// Generates a SHAKE256 hash and returns it as English-like words.
///
/// Uses an n-gram language model trained on English words to generate
/// pronounceable output. SHAKE256 provides extendable output, allowing
/// us to generate exactly the entropy needed for each word.
///
/// # Examples
///
/// ```rust
/// use readable_hash::english_word_hash;
///
/// let words = english_word_hash("hello");
/// // Returns multiple English-like words derived from the hash
/// ```
pub fn english_word_hash(input: &str) -> String {
    let mut hasher = Shake256::default();
    XofUpdate::update(&mut hasher, input.as_bytes());
    let mut reader = hasher.finalize_xof();

    // Generate multiple words using SHAKE256's extendable output
    // Each word consumes 6 bytes of entropy
    let num_words = 6;
    let mut words = Vec::with_capacity(num_words);

    for _ in 0..num_words {
        let mut entropy = [0u8; 6];
        reader.read(&mut entropy);
        let word = english_word::generate_word(&entropy);
        words.push(word);
    }

    words.join(" ")
}
