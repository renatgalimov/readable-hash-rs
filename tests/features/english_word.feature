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
