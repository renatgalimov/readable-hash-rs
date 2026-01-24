fn main() {
    println!("english_word_hash examples:");
    println!();
    println!(
        "  \"hello\" -> {}",
        readable_hash::english_word_hash("hello")
    );
    println!(
        "  \"world\" -> {}",
        readable_hash::english_word_hash("world")
    );
    println!(
        "  \"test\"  -> {}",
        readable_hash::english_word_hash("test")
    );
    println!("  \"foo\"   -> {}", readable_hash::english_word_hash("foo"));
    println!();
    println!("naive_readable_hash for comparison:");
    println!(
        "  \"hello\" -> {}",
        readable_hash::naive_readable_hash("hello")
    );
}
