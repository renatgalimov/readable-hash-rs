//! Hashes like `a7b9c3d4e5f6...` are hard to read, compare, and remember.
//! This crate transforms hash bytes into pronounceable text, making them
//! easier on human eyes.
//!
//! You might use this when verifying file integrity visually, or when you
//! need consistent pseudonyms for names and addresses without caring much
//! about cryptographic strength. It's also handy during debugging when you
//! want to quickly tell hashes apart.
//!
//! This crate is not trying to be the most secure, fastest, or most
//! entropy-efficient solution. The goal is simply readability.

use std::hash::{DefaultHasher, Hasher};

#[cfg(feature = "shake256")]
use sha3::Shake256;
#[cfg(feature = "shake256")]
use sha3::digest::{ExtendableOutput, Update as XofUpdate, XofReader};

pub mod english_word;
mod traits;

// ============================================================================
// Core Traits
// ============================================================================

/// Trait for reading bytes from a hash output.
pub trait ByteReader {
    /// Read bytes into the destination buffer. Returns bytes read.
    fn read(&mut self, dest: &mut [u8]) -> usize;

    /// Returns remaining bytes, or `None` if infinite.
    fn remaining(&self) -> Option<usize>;
}

/// Trait for hashers that produce readable hashes.
pub trait ReadableHasher: Default {
    type Reader: ByteReader;

    fn update(&mut self, data: &[u8]);
    fn finalize(self) -> Self::Reader;
}

// ============================================================================
// StdHasher (8 bytes output)
// ============================================================================

#[derive(Default)]
pub struct StdHasher<H: Hasher + Default = DefaultHasher> {
    hasher: H,
}

impl<H: Hasher + Default> ReadableHasher for StdHasher<H> {
    type Reader = StdHasherReader;

    fn update(&mut self, data: &[u8]) {
        self.hasher.write(data);
    }

    fn finalize(self) -> Self::Reader {
        StdHasherReader {
            bytes: self.hasher.finish().to_le_bytes(),
            position: 0,
        }
    }
}

pub struct StdHasherReader {
    bytes: [u8; 8],
    position: usize,
}

impl ByteReader for StdHasherReader {
    fn read(&mut self, dest: &mut [u8]) -> usize {
        let available = 8 - self.position;
        let bytes_to_read = dest.len().min(available);
        dest[..bytes_to_read]
            .copy_from_slice(&self.bytes[self.position..self.position + bytes_to_read]);
        self.position += bytes_to_read;
        bytes_to_read
    }

    fn remaining(&self) -> Option<usize> {
        Some(8 - self.position)
    }
}

// ============================================================================
// Shake256Hasher (infinite output)
// ============================================================================

#[cfg(feature = "shake256")]
#[derive(Default)]
pub struct Shake256Hasher {
    hasher: Shake256,
}

#[cfg(feature = "shake256")]
impl ReadableHasher for Shake256Hasher {
    type Reader = Shake256Reader;

    fn update(&mut self, data: &[u8]) {
        XofUpdate::update(&mut self.hasher, data);
    }

    fn finalize(self) -> Self::Reader {
        Shake256Reader {
            reader: self.hasher.finalize_xof(),
        }
    }
}

#[cfg(feature = "shake256")]
pub struct Shake256Reader {
    reader: sha3::Shake256Reader,
}

#[cfg(feature = "shake256")]
impl ByteReader for Shake256Reader {
    fn read(&mut self, dest: &mut [u8]) -> usize {
        XofReader::read(&mut self.reader, dest);
        dest.len()
    }

    fn remaining(&self) -> Option<usize> {
        None
    }
}

// ============================================================================
// SliceReader - ByteReader for byte slices
// ============================================================================

/// A ByteReader that wraps a byte slice.
pub struct SliceReader<'a> {
    data: &'a [u8],
    position: usize,
}

impl<'a> SliceReader<'a> {
    pub fn new(data: &'a [u8]) -> Self {
        Self { data, position: 0 }
    }
}

impl<'a> ByteReader for SliceReader<'a> {
    fn read(&mut self, dest: &mut [u8]) -> usize {
        let available = self.data.len() - self.position;
        let bytes_to_read = dest.len().min(available);
        dest[..bytes_to_read]
            .copy_from_slice(&self.data[self.position..self.position + bytes_to_read]);
        self.position += bytes_to_read;
        bytes_to_read
    }

    fn remaining(&self) -> Option<usize> {
        Some(self.data.len() - self.position)
    }
}

// ============================================================================
// Syllables
// ============================================================================

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

// ============================================================================
// Public API
// ============================================================================

/// Generate naive readable hash (syllable-based).
///
/// For finite hashers, uses all available bytes.
/// For infinite hashers, reads bytes proportional to input length (minimum 8).
pub fn naive_readable_hash<H, T>(input: T) -> String
where
    H: ReadableHasher,
    T: AsRef<[u8]>,
{
    let input_bytes = input.as_ref();
    if input_bytes.is_empty() {
        return String::new();
    }
    let input_len = input_bytes.len();

    let mut hasher = H::default();
    hasher.update(input_bytes);
    let mut reader = hasher.finalize();

    let bytes_to_read = match reader.remaining() {
        Some(remaining) => remaining,
        None => input_len.max(8),
    };

    let mut entropy = vec![0u8; bytes_to_read];
    reader.read(&mut entropy);

    entropy
        .iter()
        .map(|byte| SYLLABLES[*byte as usize])
        .collect()
}

/// Generate english-like word hash.
///
/// Reads bytes from the hasher and generates a single continuous word.
/// For finite hashers, uses all available bytes.
/// For infinite hashers, reads bytes proportional to input length (minimum 8).
///
/// # Examples
/// ```
/// use readable_hash::{english_word_hash, StdHasher};
///
/// assert_eq!(english_word_hash::<StdHasher, _>("I"), "waged");
/// assert_eq!(english_word_hash::<StdHasher, _>("different"), "imaumates");
/// assert_eq!(
///     english_word_hash::<StdHasher, _>("pneumonoultramicroscopicsilicovolcanoconiosis"),
///     "dummaricardemastria"
/// );
/// ```
pub fn english_word_hash<H, T>(input: T) -> String
where
    H: ReadableHasher,
    T: AsRef<[u8]>,
{
    let input_bytes = input.as_ref();
    if input_bytes.is_empty() {
        return String::new();
    }
    let input_len = input_bytes.len();

    let mut hasher = H::default();
    hasher.update(input_bytes);
    let reader = hasher.finalize();

    // For infinite readers, wrap with a length limiter
    let bytes_limit = match reader.remaining() {
        Some(_) => None,                // Finite: use all
        None => Some(input_len.max(8)), // Infinite: limit to input length
    };

    let mut limited_reader = LimitedByteReader::new(reader, bytes_limit);
    english_word::generate_word_with_target_len(&mut limited_reader, input_len)
}

/// A ByteReader wrapper that limits the number of bytes read.
struct LimitedByteReader<R: ByteReader> {
    inner: R,
    remaining: Option<usize>,
}

impl<R: ByteReader> LimitedByteReader<R> {
    fn new(inner: R, limit: Option<usize>) -> Self {
        Self {
            inner,
            remaining: limit,
        }
    }
}

impl<R: ByteReader> ByteReader for LimitedByteReader<R> {
    fn read(&mut self, dest: &mut [u8]) -> usize {
        let max_read = match self.remaining {
            Some(remaining) if remaining == 0 => return 0,
            Some(remaining) => dest.len().min(remaining),
            None => dest.len(),
        };

        let bytes_read = self.inner.read(&mut dest[..max_read]);
        if let Some(ref mut remaining) = self.remaining {
            *remaining = remaining.saturating_sub(bytes_read);
        }
        bytes_read
    }

    fn remaining(&self) -> Option<usize> {
        match (self.remaining, self.inner.remaining()) {
            (Some(limit), Some(inner_remaining)) => Some(limit.min(inner_remaining)),
            (Some(limit), None) => Some(limit),
            (None, inner_remaining) => inner_remaining,
        }
    }
}
