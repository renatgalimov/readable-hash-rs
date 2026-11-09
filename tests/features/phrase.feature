Feature: Reversible phrases
  Any 64-bit number becomes a pronounceable phrase, and the phrase decodes back to the number.

  Scenario Outline: Known numbers have known phrases
    Given the number "<number>"
    When the number is encoded as a phrase
    Then the result should be "<phrase>"
    And the phrase should decode to the number

    Examples:
      | number             | phrase                  |
      | 0x0                | maan maan maan matambar |
      | 0x2a               | parton matara matambar  |
      | 0x75bcd15          | imia quientar maan maan |
      | 0x243f6a8885a308d3 | inon nekera esam weenza |
      | 0xdeadbeefcafebabe | kibilmia umshela todans |
      | 0xffffffffffffffff | jehopalo jehopalo jeis  |

  Scenario Outline: Text that is not a canonical phrase is rejected
    Given the phrase "<text>"
    Then the phrase should not decode

    Examples:
      | text                                |
      | Inon nekera esam weenza             |
      | inon  nekera esam weenza            |
      | inon nekera esam                    |
      | inon nekera esam weenzax            |
      | matambar matambar matambar matambar |
      | hello world again                   |
