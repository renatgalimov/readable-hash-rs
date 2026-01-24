Feature: Generate English-like words from hash

  Scenario Outline: hashing strings
    Given the input "<input>"
    When the english word hash is generated
    Then the result should be "<output>"

    Examples:
      | input | output                                                       |
      | hello | magnaux crossues rejuring quizaches sublizes olemented       |
      | world | dabberies gateja pennomic mirobbed chilefied hoghtened       |
      | test  | yttington glomerate engioned slapture prieverence appleinus  |
      |       | roubbility amerimented buntimented silentine youndron fewyse |
