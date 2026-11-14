Feature: Reversible phrases
  Any 64-bit number becomes a pronounceable phrase, and the phrase decodes back to the number.

  Scenario Outline: Known numbers have known phrases
    Given the number "<number>"
    When the number is encoded as a phrase
    Then the result should be "<phrase>"
    And the phrase should decode to the number

    Examples:
      | number             | phrase                   |
      | 0x0                | maan maan maan mataizin  |
      | 0x2a               | partas matara mataizin   |
      | 0x75bcd15          | heim erkerege maan maan  |
      | 0x243f6a8885a308d3 | mung kiroot niun yeekwa  |
      | 0xdeadbeefcafebabe | vajaerna ilmiut garuzi   |
      | 0xffffffffffffffff | iteahuika iteahuika itde |

  Scenario Outline: Text that is not a canonical phrase is rejected
    Given the phrase "<text>"
    Then the phrase should not decode

    Examples:
      | text                                |
      | Mung kiroot niun yeekwa             |
      | mung  kiroot niun yeekwa            |
      | mung kiroot niun                    |
      | mung kiroot niun yeekwax            |
      | mataizin mataizin mataizin mataizin |
      | hello world again                   |
