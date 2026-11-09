Feature: Reversible phrases
  Any 64-bit number becomes a pronounceable phrase, and the phrase decodes back to the number.

  Scenario Outline: Known numbers have known phrases
    Given the number "<number>"
    When the number is encoded as a phrase
    Then the result should be "<phrase>"
    And the phrase should decode to the number

    Examples:
      | number             | phrase                    |
      | 0x0                | maan maan maan mangkawana |
      | 0x2a               | kaan mangkawana maan maan |
      | 0x75bcd15          | humpotle kaan maan mangwa |
      | 0x243f6a8885a308d3 | bomoke ankadatu embukiki  |
      | 0xdeadbeefcafebabe | foliqununda thains keltam |
      | 0xffffffffffffffff | avayliqusi avaylihan avee |

  Scenario Outline: Text that is not a canonical phrase is rejected
    Given the phrase "<text>"
    Then the phrase should not decode

    Examples:
      | text                      |
      | Bomoke ankadatu embukiki  |
      | bomoke  ankadatu embukiki |
      | bomoke ankadatu           |
      | bomoke ankadatu embukikix |
      | hello world again         |
