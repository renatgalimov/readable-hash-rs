Feature: Reversible phrases
  Any 64-bit number becomes a pronounceable phrase, and the phrase decodes back to the number.

  Scenario Outline: Known numbers have known phrases
    Given the number "<number>"
    When the number is encoded as a phrase
    Then the result should be "<phrase>"
    And the phrase should decode to the number

    Examples:
      | number             | phrase                     |
      | 0x0                | mana mana mana matambiamo  |
      | 0x2a               | kaan matambiamo mana mana  |
      | 0x75bcd15          | frifarkan kaan mana matara |
      | 0x243f6a8885a308d3 | gungwe antabaka yeeljila   |
      | 0xdeadbeefcafebabe | louvilupya brages keltet   |
      | 0xffffffffffffffff | jenogaafre jenoganu jega   |

  Scenario Outline: Text that is not a canonical phrase is rejected
    Given the phrase "<text>"
    Then the phrase should not decode

    Examples:
      | text                      |
      | Gungwe antabaka yeeljila  |
      | gungwe  antabaka yeeljila |
      | gungwe antabaka           |
      | gungwe antabaka yeeljilax |
      | hello world again         |
