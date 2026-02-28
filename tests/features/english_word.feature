Feature: Generate English-like words from hash

  Background:
    Given using the std hasher

  Scenario Outline: hashing strings produces expected output
    Given the input "<input>"
    When the english word hash is generated
    Then the result should be "<output>"

    Examples:
      | input | output       |
      | hello | doses |
      | world | dieth |
      | test  | waster |
      |       |                  |

  Scenario Outline: all hashes are single words
    Given the input "<input>"
    When the english word hash is generated
    Then the result should be a single word

    Examples:
      | input       |
      | hello       |
      | world       |
      | test        |
      |             |
      | foo         |
      | longer text |

  Scenario Outline: generate_word from bytes
    Given the entropy bytes "<hex>"
    When a word is generated from the entropy
    Then the result should be "<output>"

    Examples:
      | hex          | output   |
      | DEADBEEF     | barried |
      | DEADBEEFCAFE | barrieved |
      | 00000000     | revers |
      | FFFFFFFF     | ovens |

  Scenario: generate_word handles empty entropy
    Given the entropy bytes ""
    When a word is generated from the entropy
    Then the result should be ""
