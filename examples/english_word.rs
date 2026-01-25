use readable_hash::{english_word_hash, naive_readable_hash, StdHasher};
#[cfg(feature = "shake256")]
use readable_hash::Shake256Hasher;

fn main() {
    println!("StdHasher examples:");
    println!("  english_word_hash(\"hello\") -> {}", english_word_hash::<StdHasher, _>("hello"));
    println!("  english_word_hash(\"world\") -> {}", english_word_hash::<StdHasher, _>("world"));
    println!("  english_word_hash(\"test\")  -> {}", english_word_hash::<StdHasher, _>("test"));
    println!("  english_word_hash(\"\")      -> {}", english_word_hash::<StdHasher, _>(""));
    println!("  naive_readable_hash(\"hello\") -> {}", naive_readable_hash::<StdHasher, _>("hello"));

    #[cfg(feature = "shake256")]
    {
        println!();
        println!("Shake256Hasher examples:");
        println!("  english_word_hash(\"hello\") -> {}", english_word_hash::<Shake256Hasher, _>("hello"));
        println!("  english_word_hash(\"world\") -> {}", english_word_hash::<Shake256Hasher, _>("world"));
        println!("  english_word_hash(\"test\")  -> {}", english_word_hash::<Shake256Hasher, _>("test"));
        println!("  english_word_hash(\"\")      -> {}", english_word_hash::<Shake256Hasher, _>(""));
        println!("  naive_readable_hash(\"hello\") -> {}", naive_readable_hash::<Shake256Hasher, _>("hello"));
    }
}
