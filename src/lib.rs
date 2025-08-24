use sha2::{Digest, Sha256};

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
    "il", "his", "ir", "all", "for", "was ", "id", "de", "with ", "et", "that ", "be", "ut", "ic",
    "us", "el", "ur", "he", "ent ", "as", "or", "al", "ar", "is", "an", "u", "ing ", "at", "it",
    "es", "to", "and ", "en", "on", "of", "ed ", "o", "in", "er", "i", "a", "y", "the ", "e",
];

/// Generates a SHA-256 hash and returns it as a syllable string.
pub fn readable_hash(input: &str) -> String {
    let mut hasher = Sha256::new();
    hasher.update(input.as_bytes());
    let result = hasher.finalize();
    result
        .iter()
        .map(|b| SYLLABLES[*b as usize])
        .collect::<String>()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn hashes_consistently() {
        let expected = "ungtoattmeertantdipresecorvisuchosfromusellremight itthasissupfeprojthemuthveroff abljahimiz";
        assert_eq!(readable_hash("hello"), expected);
    }
}
