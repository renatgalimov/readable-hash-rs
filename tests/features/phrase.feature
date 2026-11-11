Feature: Reversible phrases
  Any 64-bit number becomes a pronounceable phrase, and the phrase decodes back to the number.

  Scenario Outline: Known numbers have known phrases
    Given the number "<number>"
    When the number is encoded as a phrase
    Then the result should be "<phrase>"
    And the phrase should decode to the number

    Examples:
      | number             | phrase                   |
      | 0x0                | maan maan maan makatara  |
      | 0x2a               | partes makana makatara   |
      | 0x75bcd15          | adom aguerege maan maan  |
      | 0x243f6a8885a308d3 | sain aralin suit umadde  |
      | 0xdeadbeefcafebabe | chavicho sheplo ganyay   |
      | 0xffffffffffffffff | dhateguit dhateguit dhiz |

  Scenario Outline: Text that is not a canonical phrase is rejected
    Given the phrase "<text>"
    Then the phrase should not decode

    Examples:
      | text                                |
      | Sain aralin suit umadde             |
      | sain  aralin suit umadde            |
      | sain aralin suit                    |
      | sain aralin suit umaddex            |
      | makatara makatara makatara makatara |
      | hello world again                   |
