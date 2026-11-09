Feature: Reversible phrases
  Any 64-bit number becomes a pronounceable phrase, and the phrase decodes back to the number.

  Scenario Outline: Known numbers have known phrases
    Given the number "<number>"
    When the number is encoded as a phrase
    Then the result should be "<phrase>"
    And the phrase should decode to the number

    Examples:
      | number             | phrase                    |
      | 0x0                | maas maas maas manggunaki |
      | 0x2a               | kaan manggunaki maas maas |
      | 0x75bcd15          | spinquos kaan maas mangwa |
      | 0x243f6a8885a308d3 | bongere siuninut nuunamus |
      | 0xdeadbeefcafebabe | aileivirda fraash kesavo  |
      | 0xffffffffffffffff | luboaleuia luboaldo luar  |

  Scenario Outline: Text that is not a canonical phrase is rejected
    Given the phrase "<text>"
    Then the phrase should not decode

    Examples:
      | text                       |
      | Bongere siuninut nuunamus  |
      | bongere  siuninut nuunamus |
      | bongere siuninut           |
      | bongere siuninut nuunamusx |
      | hello world again          |
