Feature: Reversible phrases
  Any 64-bit number becomes an English-like phrase, and the phrase decodes back to the number.

  Scenario Outline: Known numbers have known phrases
    Given the number "<number>"
    When the number is encoded as a phrase
    Then the result should be "<phrase>"
    And the phrase should decode to the number

    Examples:
      | number             | phrase                           |
      | 0x0                | redes redes redes reversitation  |
      | 0x2a               | unable reversitation redes redes |
      | 0x75bcd15          | tumenald unable redes reverted   |
      | 0x243f6a8885a308d3 | dalmse prospicity cindrable      |
      | 0xdeadbeefcafebabe | ceiloparms atkits taboes         |
      | 0xffffffffffffffff | jabaltiddes jabaltous jaic       |

  Scenario Outline: Text that is not a canonical phrase is rejected
    Given the phrase "<text>"
    Then the phrase should not decode

    Examples:
      | text                          |
      | Dalmse prospicity cindrable   |
      | dalmse  prospicity cindrable  |
      | dalmse prospicity             |
      | dalmse prospicity cindrablex  |
      | hello world again             |
