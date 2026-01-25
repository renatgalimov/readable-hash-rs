Feature: Generate English-like words from hash

  Scenario Outline: hashing strings
    Given the input "<input>"
    When the english word hash is generated
    Then the result should be "<output>"

    Examples:
      | input | output                                       |
      | hello | magnaunguineymwaiticolimercipid              |
      | world | dabberimentatigollertujaniardalgerian        |
      | test  | yttinghillamsbiassiveringaywitchi            |
      |       | roubbirthyreniefoominatomitantinizing        |

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
    When a word is generated with max <max_tokens> tokens
    Then the result should be "<output>"

    Examples:
      | hex                              | max_tokens | output                            |
      | DEADBEEF                         | 16         | symore                            |
      | DEADBEEFCAFE                     | 16         | symorius                          |
      | 00000000                         | 16         | revers                            |
      | FFFFFFFF                         | 16         | ovens                             |

  Scenario Outline: generate_word respects max_tokens
    Given the entropy bytes "DEADBEEFCAFEBABE1234567890ABCDEF"
    When a word is generated with max <max_tokens> tokens
    Then the result should have at most <max_tokens> tokens

    Examples:
      | max_tokens |
      | 2          |
      | 4          |
      | 8          |
      | 16         |

  Scenario: generate_word handles empty entropy
    Given the entropy bytes ""
    When a word is generated with max 16 tokens
    Then the result should be ""
